mod api;
mod chat;
mod settings;
mod types;

use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::Manager;  // get_webview_window 등 창 관리 메서드에 필요
use types::Cookies;

/// 채팅 워커 task의 AbortHandle 보관.
/// connect_chat으로 task를 시작하고, disconnect_chat으로 중단.
struct ChatState(Mutex<Option<tokio::task::AbortHandle>>);
// Mutex<Option<AbortHandle>> 문법이 좀 낯선데, 설명이 필요해.

/// settings.json, log/ 등 앱 파일을 읽고 쓸 디렉토리 반환.
/// dev: 프로젝트 루트 (exe 4단계 위, cookies.json이 있는 곳)
/// 배포: 실행 파일 옆 디렉토리
fn app_dir() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;

    // dev 환경: cookies.json이 있는 프로젝트 루트를 우선
    // 주석: ancestors().nth() 와 같은 방식말고 좀더 안전하고, 좋은 방법이 없을까?
    // 아니면 이게 Rust 권장방식인가?
    if let Some(dir) = exe.ancestors().nth(4) {
        if dir.join("cookies.json").exists() {
            return Ok(dir.to_path_buf());
        }
    }
    // 배포: 실행 파일 옆
    exe.parent()
        .map(|p| p.to_path_buf())
        .ok_or("실행 파일 경로를 찾을 수 없습니다".to_string())
    // 주석: .map(|p| p.to_path_buf()) 와 같은 문법도 설명해줘
}

fn load_cookies() -> Result<Cookies, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;

    // 탐색할 후보 경로 목록
    // 1) 실행 파일 옆 (배포 환경)
    // 2) 4단계 위 (dev: .../src-tauri/target/debug/exe → ... → 프로젝트 루트)
    // TODO: 현재 dev 환경에서는 잘 작동함. 그런데 배포시에도 이런 방식이 괜찮을까?
    let candidates: Vec<_> = [
        exe.parent().map(|d| d.join("cookies.json")),
        exe.ancestors().nth(4).map(|d| d.join("cookies.json")),
    ]
    .into_iter()
    .flatten()
    .collect();

    for path in &candidates {
        if path.exists() {
            let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
            return serde_json::from_str::<Cookies>(&content).map_err(|e| e.to_string());
        }
    }

    Err(format!(
        "cookies.json을 찾을 수 없습니다. 탐색한 경로: {:?}",
        candidates
    ))
}

/// 저장된 설정을 반환. 없으면 기본값.
#[tauri::command]
fn get_settings() -> settings::Settings {
    app_dir()
        .map(|dir| settings::load(&dir))
        .unwrap_or_default()
}

/// 설정을 settings.json에 저장.
#[tauri::command]
fn save_settings(s: settings::Settings) -> Result<(), String> {
    settings::save(&app_dir()?, &s)
}

/// 연결에 필요한 정보를 조회하고 채팅 워커(WebSocket) 시작.
/// 첨부: #[tauri::command] 는 어떤 기능이지? python의 @decorator 같은 기능인가?
/// 첨부: 어느 fn이나 [tauri::command]를 붙이면 뭐든 invoke 할수있게 되는건가?
#[tauri::command]
async fn connect_chat(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, ChatState>, // 이 문법은 이해가 잘 안가
    streamer_uid: String,
) -> Result<serde_json::Value, String> {
    let cookies = load_cookies()?;

    // 채널 이름과 채팅 채널 ID 병렬 조회
    let (channel_name, chat_channel_id) = tokio::try_join!(
        api::fetch_channel_name(&streamer_uid),
        api::fetch_chat_channel_id(&streamer_uid, &cookies.nid_aut, &cookies.nid_ses),
    )?;

    // 액세스 토큰과 유저 해시 병렬 조회
    let (token_result, user_id_hash) = tokio::try_join!(
        api::fetch_access_token(&chat_channel_id, &cookies.nid_aut, &cookies.nid_ses),
        api::fetch_user_id_hash(&cookies.nid_aut, &cookies.nid_ses),
    )?;
    let (access_token, _extra_token) = token_result;

    // 로그 디렉토리: {app_dir}/log/{channel_name}/
    let log_dir = app_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("log")
        .join(&channel_name);

    // 이미지 캐시 디렉토리: {app_dir}/cache/{channel_name}/
    let cache_dir = app_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("cache")
        .join(&channel_name);

    // 기존 채팅 워커가 있으면 먼저 중단
    if let Some(handle) = state.0.lock().unwrap().take() {
        handle.abort();
    }

    // 채팅 워커를 백그라운드 task로 실행
    let task = tokio::spawn(chat::run(
        app_handle,
        streamer_uid,
        cookies.nid_aut,
        cookies.nid_ses,
        chat_channel_id.clone(),
        access_token,
        user_id_hash,
        log_dir,
        cache_dir,
    ));
    *state.0.lock().unwrap() = Some(task.abort_handle());

    Ok(serde_json::json!({
        "channel_name": channel_name,
        "chat_channel_id": chat_channel_id,
    }))
}

/// 채팅 워커 중단
#[tauri::command]
fn disconnect_chat(state: tauri::State<'_, ChatState>) {
    if let Some(handle) = state.0.lock().unwrap().take() {
        handle.abort();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(ChatState(Mutex::new(None)))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .invoke_handler(tauri::generate_handler![
            connect_chat,
            disconnect_chat,
            get_settings,
            save_settings,
        ])
        .setup(|app| {
            // 시스템 트레이 설정
            // app.default_window_icon(): tauri.conf.json의 bundle.icon에서 자동 로드됨
            let icon = app.default_window_icon()
                .expect("아이콘 로드 실패")
                .clone();
            let _tray = tauri::tray::TrayIconBuilder::new()
                .icon(icon)
                .tooltip("ChzzkChat")
                // 트레이 아이콘 클릭 → 창 표시/숨기기 토글
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click {
                        button: tauri::tray::MouseButton::Left,
                        button_state: tauri::tray::MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(win) = app.get_webview_window("main") {
                            if matches!(win.is_visible(), Ok(true)) {
                                // matches! 매크로없을때 에러는 왜 발생한거고, 왜 수정한거야?
                                let _ = win.hide();
                            } else {
                                let _ = win.show();
                                let _ = win.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}