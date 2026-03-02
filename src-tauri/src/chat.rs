use chrono::TimeZone;
use futures_util::{SinkExt, StreamExt};
use serde_json::json;
use std::collections::HashMap;
use std::io::Write;
use std::path::{Path, PathBuf};
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
    log_dir: PathBuf,
    cache_dir: PathBuf,
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
            &cache_dir,
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
    cache_dir: &PathBuf,
) -> Result<(), String> {
    let (ws_stream, _) = connect_async(WS_URL)
        .await
        .map_err(|e| e.to_string())?;
    let (mut write, mut read) = ws_stream.split();

    // HTTP 클라이언트: 이미지 캐시 다운로드에 재사용
    let http_client = reqwest::Client::new();

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
    read.next().await; // 최근 채팅 응답은 스킵

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
                        if let Some(mut chat) = parse_chat(item, chat_type) {
                            cache_images(&mut chat, cache_dir, &http_client).await;
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

    // extras를 한 번만 파싱해서 os_type과 emojis 동시 추출
    let extras: Option<serde_json::Value> = data["extras"]
        .as_str()
        .and_then(|s| serde_json::from_str(s).ok());

    // 주석: os_type은 왜 저장하는거고, 지금은 어디에 사용되고있어?
    let os_type = extras
        .as_ref()
        .and_then(|e| e["osType"].as_str().map(str::to_string))
        .unwrap_or_default();

    // 메시지에서 실제 사용된 이모지 이름만 추출 ({:name:} 패턴)
    // Chzzk API는 extras.emojis에 채널 이모지 세트 전체를 매 메시지마다 전송하므로
    // 사용된 것만 필터링하지 않으면 20,000건 × N이모지 = JS 힙 폭증
    let used_emojis: std::collections::HashSet<&str> = {
        let mut set = std::collections::HashSet::new();
        let mut s = message.as_str();
        while let Some(start) = s.find("{:") {
            s = &s[start + 2..];
            if let Some(end) = s.find(":}") {
                set.insert(&s[..end]);
                s = &s[end + 2..];
            } else {
                break;
            }
        }
        set
    };

    let emojis: HashMap<String, String> = extras
        .as_ref()
        .and_then(|e| e["emojis"].as_object())
        .map(|obj| {
            obj.iter()
                .filter(|(k, _)| used_emojis.contains(k.as_str()))
                .map(|(k, v)| (k.clone(), v.as_str().unwrap_or("").to_string()))
                .collect()
        })
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
            emojis,
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
        emojis,
        subscription_month,
        os_type,
        user_role,
    })
}

/// URL → 캐시 파일 경로 계산 (DefaultHasher 사용, 외부 crate 불필요)
fn url_to_cache_path(url: &str, cache_dir: &Path) -> PathBuf {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut hasher = DefaultHasher::new();
    url.hash(&mut hasher);
    let hash = hasher.finish();
    // URL에서 확장자 추출 ('?' 이전 부분의 마지막 .ext)
    let ext = url
        .split('?')
        .next()
        .and_then(|s| s.rsplit('.').next())
        .filter(|e| e.len() <= 5)
        .unwrap_or("webp");
    cache_dir.join(format!("{:016x}.{}", hash, ext))
}

/// 이미지 URL → 로컬 캐시 파일 경로 반환.
/// 이미 캐시되어 있으면 즉시 반환, 없으면 다운로드 후 저장.
/// 실패 시 원본 URL 그대로 반환 (네트워크 직접 로드 폴백).
async fn cache_image(url: &str, cache_dir: &Path, client: &reqwest::Client) -> String {
    if url.is_empty() {
        return url.to_string();
    }
    let path = url_to_cache_path(url, cache_dir);
    if path.exists() {
        return path.to_string_lossy().to_string();
    }
    if let Ok(()) = std::fs::create_dir_all(cache_dir) {
        if let Ok(resp) = client.get(url).send().await {
            if let Ok(bytes) = resp.bytes().await {
                let _ = std::fs::write(&path, &bytes);
                return path.to_string_lossy().to_string();
            }
        }
    }
    url.to_string()
}

/// ChatData 내 모든 배지/이모지 URL을 로컬 캐시 경로로 교체
async fn cache_images(chat: &mut ChatData, cache_dir: &Path, client: &reqwest::Client) {
    for url in chat.badges.iter_mut() {
        *url = cache_image(url, cache_dir, client).await;
    }
    for url in chat.emojis.values_mut() {
        *url = cache_image(url, cache_dir, client).await;
    }
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
        {   // 질문: 여기에 괄호는 왜 이렇게 한줄 아래에 만든거야? 권장되는 형태야?
            let _ = file.write_all(line.as_bytes());
        }
    }
}