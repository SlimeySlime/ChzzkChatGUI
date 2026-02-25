use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Serialize, Deserialize, Clone)]
pub struct Settings {
    pub font_size: u32,
    pub show_timestamp: bool,
    pub show_badges: bool,
    pub donation_only: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            font_size: 13,
            show_timestamp: true,
            show_badges: true,
            donation_only: false,
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
