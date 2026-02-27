use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct ChatData {
    pub time: String,
    pub chat_type: String,       // "채팅" | "후원"
    pub uid: String,
    pub nickname: String,
    pub message: String,
    pub color_code: String,
    pub badges: Vec<String>,     // 이미지 로컬경로 or URL (최대 3개)
    pub emojis: HashMap<String, String>,  // {이모지이름: 로컬경로 or URL}
    pub subscription_month: u32,
    pub os_type: String,         // "PC" | "MOBILE"
    pub user_role: String,       // "common_user" | "manager" | "streamer"
}

#[derive(Deserialize)]
pub struct Cookies {
    #[serde(rename = "NID_AUT")]
    pub nid_aut: String,
    #[serde(rename = "NID_SES")]
    pub nid_ses: String,
}