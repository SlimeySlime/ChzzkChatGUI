use reqwest::{Client, header};

fn make_client(nid_aut: &str, nid_ses: &str) -> Result<Client, String> {
    let cookie = format!("NID_AUT={}; NID_SES={}", nid_aut, nid_ses);
    Client::builder()
        .default_headers({
            let mut headers = header::HeaderMap::new();
            headers.insert(header::USER_AGENT, header::HeaderValue::from_static(""));
            headers.insert(
                header::COOKIE,
                header::HeaderValue::from_str(&cookie)
                    .map_err(|e| e.to_string())?,
            );
            headers
        })
        .build()
        .map_err(|e| e.to_string())
}

/// 채팅 채널 ID 조회 (방송 중일 때만 값 있음)
pub async fn fetch_chat_channel_id(
    streamer: &str,
    nid_aut: &str,
    nid_ses: &str,
) -> Result<String, String> {
    let client = make_client(nid_aut, nid_ses)?;
    let url = format!(
        "https://api.chzzk.naver.com/polling/v2/channels/{}/live-status",
        streamer
    );
    let resp: serde_json::Value = client
        .get(&url)
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())?;

    let chat_channel_id = resp["content"]["chatChannelId"]
        .as_str()
        .ok_or("chatChannelId가 없습니다 (방송이 꺼져 있을 수 있음)")?
        .to_string();
    Ok(chat_channel_id)
}

/// 채널 이름 조회
pub async fn fetch_channel_name(streamer: &str) -> Result<String, String> {
    let client = Client::builder()
        .default_headers({
            let mut headers = header::HeaderMap::new();
            headers.insert(header::USER_AGENT, header::HeaderValue::from_static(""));
            headers
        })
        .build()
        .map_err(|e| e.to_string())?;

    let url = format!(
        "https://api.chzzk.naver.com/service/v1/channels/{}",
        streamer
    );
    let resp: serde_json::Value = client
        .get(&url)
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())?;

    let name = resp["content"]["channelName"]
        .as_str()
        .ok_or("channelName이 없습니다")?
        .to_string();
    Ok(name)
}

/// 액세스 토큰 발급 (accessToken, extraToken)
pub async fn fetch_access_token(
    chat_channel_id: &str,
    nid_aut: &str,
    nid_ses: &str,
) -> Result<(String, String), String> {
    let client = make_client(nid_aut, nid_ses)?;
    let url = format!(
        "https://comm-api.game.naver.com/nng_main/v1/chats/access-token?channelId={}&chatType=STREAMING",
        chat_channel_id
    );
    let resp: serde_json::Value = client
        .get(&url)
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())?;

    let access_token = resp["content"]["accessToken"]
        .as_str()
        .ok_or("accessToken이 없습니다")?
        .to_string();
    let extra_token = resp["content"]["extraToken"]
        .as_str()
        .ok_or("extraToken이 없습니다")?
        .to_string();
    Ok((access_token, extra_token))
}

/// 사용자 ID 해시 조회
pub async fn fetch_user_id_hash(nid_aut: &str, nid_ses: &str) -> Result<String, String> {
    let client = make_client(nid_aut, nid_ses)?;
    let url = "https://comm-api.game.naver.com/nng_main/v1/user/getUserStatus";
    let resp: serde_json::Value = client
        .get(url)
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())?;

    let user_id_hash = resp["content"]["userIdHash"]
        .as_str()
        .ok_or("userIdHash가 없습니다")?
        .to_string();
    Ok(user_id_hash)
}
