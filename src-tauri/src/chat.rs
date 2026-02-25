use chrono::TimeZone;
use futures_util::{SinkExt, StreamExt};
use serde_json::json;
use std::io::Write;
use std::path::PathBuf;
use tauri::Emitter;
use tokio_tungstenite::{connect_async, tungstenite::Message};

use crate::{api, types::ChatData};

const WS_URL: &str = "wss://kr-ss1.chat.naver.com/chat";

/// 채팅 워커 메인 루프.
/// connect_chat 커맨드에서 tokio::spawn으로 실행됨.
/// 연결 끊기면 5초 대기 후 재연결, AbortHandle로 외부에서 중단 가능.
pub async fn run(
    app_handle: tauri::AppHandle,
    streamer_uid: String,
    nid_aut: String,
    nid_ses: String,
    mut chat_channel_id: String,
    mut access_token: String,
    user_id_hash: String,
    log_dir: PathBuf,   // {app_dir}/log/{channel_name}/
) {
    loop {
        let result = chat_session(
            &app_handle,
            &streamer_uid,
            &nid_aut,
            &nid_ses,
            &chat_channel_id,
            &access_token,
            &user_id_hash,
            &log_dir,
        )
        .await;

        match result {
            Ok(()) => break, // disconnect_chat()로 인한 정상 종료 (task abort)
            Err(e) => {
                eprintln!("채팅 연결 끊김: {e}, 5초 후 재연결...");
                tokio::time::sleep(std::time::Duration::from_secs(5)).await;

                // 재연결을 위해 채널 ID, 토큰 재발급
                if let Ok(new_id) =
                    api::fetch_chat_channel_id(&streamer_uid, &nid_aut, &nid_ses).await
                {
                    chat_channel_id = new_id;
                }
                if let Ok((new_token, _)) =
                    api::fetch_access_token(&chat_channel_id, &nid_aut, &nid_ses).await
                {
                    access_token = new_token;
                }
            }
        }
    }
}

/// 한 번의 WebSocket 세션 (CONNECT → 수신 루프)
async fn chat_session(
    app_handle: &tauri::AppHandle,
    streamer_uid: &str,
    nid_aut: &str,
    nid_ses: &str,
    chat_channel_id: &str,
    access_token: &str,
    user_id_hash: &str,
    log_dir: &PathBuf,
) -> Result<(), String> {
    let (ws_stream, _) = connect_async(WS_URL)
        .await
        .map_err(|e| e.to_string())?;
    let (mut write, mut read) = ws_stream.split();

    // CONNECT 메시지 전송
    let connect_msg = json!({
        "cmd": 100, "tid": 1, "ver": "2",
        "svcid": "game", "cid": chat_channel_id,
        "bdy": {
            "uid": user_id_hash,
            "devType": 2001,
            "accTkn": access_token,
            "auth": "SEND",
        }
    });
    write
        .send(Message::text(connect_msg.to_string()))
        .await
        .map_err(|e| e.to_string())?;

    // SID 획득
    let sid = match read.next().await {
        Some(Ok(Message::Text(text))) => {
            let resp: serde_json::Value =
                serde_json::from_str(text.as_str()).map_err(|e| e.to_string())?;
            resp["bdy"]["sid"]
                .as_str()
                .ok_or("SID 없음")?
                .to_string()
        }
        _ => return Err("CONNECT 응답 없음".to_string()),
    };

    // 최근 채팅 50건 요청
    let recent_msg = json!({
        "cmd": 5101, "tid": 2, "sid": sid,
        "ver": "2", "svcid": "game", "cid": chat_channel_id,
        "bdy": { "recentMessageCount": 50 }
    });
    write
        .send(Message::text(recent_msg.to_string()))
        .await
        .map_err(|e| e.to_string())?;
    read.next().await; // 최근 채팅 응답은 스킵 (Phase 5에서 활용 예정)

    // 메인 수신 루프
    while let Some(msg_result) = read.next().await {
        match msg_result {
            Ok(Message::Text(text)) => {
                let raw: serde_json::Value = match serde_json::from_str(text.as_str()) {
                    Ok(v) => v,
                    Err(_) => continue,
                };
                let cmd = match raw["cmd"].as_u64() {
                    Some(c) => c,
                    None => continue,
                };

                // cmd:0 (서버 ping) → cmd:10000 (pong) 응답 필수
                if cmd == 0 {
                    let pong = json!({"ver": "2", "cmd": 10000});
                    let _ = write.send(Message::text(pong.to_string())).await;

                    // PING마다 채널 ID 변경 확인 (방송 재시작 감지)
                    if let Ok(new_id) =
                        api::fetch_chat_channel_id(streamer_uid, nid_aut, nid_ses).await
                    {
                        if new_id != chat_channel_id {
                            return Err("채널 ID 변경됨 (방송 재시작)".to_string());
                        }
                    }
                    continue;
                }

                let chat_type = match cmd {
                    93101 => "채팅",
                    93102 => "후원",
                    _ => continue,
                };

                if let Some(bdy) = raw["bdy"].as_array() {
                    for item in bdy {
                        if let Some(chat) = parse_chat(item, chat_type) {
                            let _ = app_handle.emit("chat-message", &chat);
                            write_log(log_dir, &chat);
                        }
                    }
                }
            }
            Ok(Message::Close(_)) => return Err("서버가 연결을 닫았습니다".to_string()),
            Err(e) => return Err(e.to_string()),
            _ => {}
        }
    }

    Ok(())
}

fn parse_chat(data: &serde_json::Value, chat_type: &str) -> Option<ChatData> {
    let uid = data["uid"].as_str()?.to_string();
    let message = data["msg"].as_str()?.to_string();
    let time = data["msgTime"].as_u64().map(format_time).unwrap_or_default();

    let os_type = data["extras"]
        .as_str()
        .and_then(|s| serde_json::from_str::<serde_json::Value>(s).ok())
        .and_then(|e| e["osType"].as_str().map(str::to_string))
        .unwrap_or_default();

    // 익명 후원자
    if uid == "anonymous" {
        return Some(ChatData {
            time,
            chat_type: chat_type.to_string(),
            uid,
            nickname: "익명의 후원자".to_string(),
            message,
            color_code: String::new(),
            badges: vec![],
            subscription_month: 0,
            os_type,
            user_role: "common_user".to_string(),
        });
    }

    let profile: serde_json::Value =
        serde_json::from_str(data["profile"].as_str()?).ok()?;

    let nickname = profile["nickname"].as_str()?.to_string();
    let user_role = profile["userRoleCode"]
        .as_str()
        .unwrap_or("common_user")
        .to_string();

    let sp = &profile["streamingProperty"];
    let color_code = sp["nicknameColor"]["colorCode"]
        .as_str()
        .unwrap_or("")
        .to_string();

    let sub = &sp["subscription"];
    let subscription_month = sub["accumulativeMonth"].as_u64().unwrap_or(0) as u32;

    let mut badges: Vec<String> = vec![];
    if let Some(url) = sub["badge"]["imageUrl"].as_str() {
        if !url.is_empty() {
            badges.push(url.to_string());
        }
    }
    for badge in profile["activityBadges"].as_array().unwrap_or(&vec![]) {
        if badge["activated"].as_bool().unwrap_or(false) {
            if let Some(url) = badge["imageUrl"].as_str() {
                if !url.is_empty() {
                    badges.push(url.to_string());
                }
            }
        }
    }
    badges.truncate(3);

    Some(ChatData {
        time,
        chat_type: chat_type.to_string(),
        uid,
        nickname,
        message,
        color_code,
        badges,
        subscription_month,
        os_type,
        user_role,
    })
}

fn format_time(ms: u64) -> String {
    chrono::Local
        .timestamp_opt((ms / 1000) as i64, 0)
        .single()
        .unwrap_or_else(chrono::Local::now)
        .format("%H:%M:%S")
        .to_string()
}

fn write_log(log_dir: &PathBuf, chat: &ChatData) {
    let date = chrono::Local::now().format("%Y-%m-%d").to_string();
    let log_path = log_dir.join(format!("{date}.log"));
    // let Ok(()) = 문법이 잘 이해안가
    if let Ok(()) = std::fs::create_dir_all(log_dir) {
        let line = if chat.chat_type == "후원" {
            format!("[{}] [후원] {}: {}\n", chat.time, chat.nickname, chat.message)
        } else {
            format!("[{}] {}: {}\n", chat.time, chat.nickname, chat.message)
        };
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
        {   // 왜 여기 괄호는 이렇게 닫은거지?
            let _ = file.write_all(line.as_bytes());
        }
    }
}