use serde::{Deserialize, Serialize};
use std::path::Path;

fn default_font_size() -> u32 { 13 }
fn default_bool_true() -> bool { true }
fn default_window_width() -> u32 { 800 }
fn default_window_height() -> u32 { 600 }
fn default_theme() -> String { "dark".into() }

#[derive(Serialize, Deserialize, Clone)]
pub struct Settings {
    // 기존 필드: 이미 저장된 settings.json에 항상 존재하므로 #[serde(default)] 불필요
    #[serde(default = "default_font_size")]
    pub font_size: u32,
    #[serde(default = "default_bool_true")]
    pub show_timestamp: bool,
    #[serde(default = "default_bool_true")]
    pub show_badges: bool,
    #[serde(default)]
    pub donation_only: bool,

    // 창 상태: 기존 settings.json에 없으므로 #[serde(default)] 필수
    // (없으면 serde 역직렬화 실패 → unwrap_or_default()로 폴백 → 기존 설정 날아감)
    #[serde(default = "default_window_width")]
    pub window_width: u32,
    #[serde(default = "default_window_height")]
    pub window_height: u32,
    #[serde(default)]
    pub window_x: Option<i32>,
    #[serde(default)]
    pub window_y: Option<i32>,

    #[serde(default = "default_theme")]
    pub theme: String,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            font_size: 13,
            show_timestamp: true,
            show_badges: true,
            donation_only: false,
            window_width: 800,
            window_height: 600,
            window_x: None,
            window_y: None,
            theme: "dark".into(),
        }
    }
}

pub fn load(app_dir: &Path) -> Settings {
    let path = app_dir.join("settings.json");
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

pub fn save(app_dir: &Path, settings: &Settings) -> Result<(), String> {
    std::fs::create_dir_all(app_dir).map_err(|e| e.to_string())?;
    let content = serde_json::to_string_pretty(settings).map_err(|e| e.to_string())?;
    std::fs::write(app_dir.join("settings.json"), content).map_err(|e| e.to_string())
}
