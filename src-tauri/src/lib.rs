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
// 질문: Mutex<Option<AbortHandle>> 문법이 좀 낯선데, 설명이 필요해.

/// settings.json, log/, cache/ 등 앱 파일을 읽고 쓸 디렉토리 반환.
/// dev:  exe가 src-tauri/target/debug/ 에 있으므로 4단계 위 = 프로젝트 루트
/// prod: 실행 파일 옆 디렉토리 (포터블 방식 — exe 옆에 cookies.json/log/cache 위치)
fn app_dir() -> Result<PathBuf, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;

    #[cfg(debug_assertions)]
    {
        // debug 빌드 전용: src-tauri/target/debug/exe → 4단계 위 = 프로젝트 루트
        // 주석: ancestors().nth() 와 같은 방식말고 좀더 안전하고, 좋은 방법이 없을까?
        // 아니면 이게 Rust 권장방식인가?
        if let Some(dir) = exe.ancestors().nth(4) {
            return Ok(dir.to_path_buf());
        }
    }

    // release 빌드: 실행 파일 옆 (exe를 어디에 두든 그 폴더를 사용)
    // 질문: .map(|p| p.to_path_buf()) 와 같은 문법도 설명해줘
    exe.parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| "실행 파일 경로를 찾을 수 없습니다".to_string())
}

fn load_cookies() -> Result<Cookies, String> {
    let path = app_dir()?.join("cookies.json");
    let content = fs::read_to_string(&path)
        .map_err(|e| format!("cookies.json 읽기 실패 ({:?}): {}", path, e))?;
    serde_json::from_str::<Cookies>(&content).map_err(|e| e.to_string())
}

/// 창의 현재 크기·위치를 settings.json에 저장.
/// Wayland 등 위치 조회가 불가한 환경에서는 위치 저장을 건너뜀.
/// 호출 시점: X 버튼(CloseRequested), 트레이 숨기기 버튼, 트레이 아이콘 클릭 숨기기
fn save_win_state(win: &tauri::WebviewWindow, dir: &PathBuf) {
    let Ok(size) = win.inner_size() else { return };
    // 질문: Ok(Size) = win.inner_size() else { return }; 문법도 설명해줘
    // Ok(Size) 는 어떤 구문이지? 
    let mut s = settings::load(dir);
    s.window_width = size.width;
    s.window_height = size.height;
    // outer_position()은 Wayland에서 실패할 수 있음 — 실패 시 기존 값 유지
    if let Ok(pos) = win.outer_position() {
        s.window_x = Some(pos.x);
        s.window_y = Some(pos.y);
    }
    let _ = settings::save(dir, &s);
}

/// 저장된 설정을 반환. 없으면 기본값.
#[tauri::command]
fn get_settings() -> settings::Settings {
    app_dir()
        .map(|dir| settings::load(&dir))
        .unwrap_or_default()
        // 질문: unwrap_or_default() 는 무슨 뜻의 함수야?
}

/// 설정을 settings.json에 저장.
#[tauri::command]
fn save_settings(s: settings::Settings) -> Result<(), String> {
    settings::save(&app_dir()?, &s)
    // Result<(), String> 타입에서 Ok(())는 성공시 빈 반환값, Err(String)은 실패 메시지 반환.
}

/// 트레이로 숨기기 전에 창 상태를 저장하고 창을 숨김.
/// MenuBar의 "트레이 아이콘" 버튼에서 호출 (프론트엔드에서 직접 hide()하면 저장 안 됨).
#[tauri::command]
fn hide_to_tray(app_handle: tauri::AppHandle) {
    if let Some(win) = app_handle.get_webview_window("main") {
        if let Ok(dir) = app_dir() {
            save_win_state(&win, &dir);
        }
        let _ = win.hide();
        // 질문: win.hide() 가 아니라, let _ = win.hide(); 한 이유는 뭐야?
    }
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

/// 더미 테스트용: 실제 캐시 이미지 경로 목록 + 로그 파싱 결과 반환
#[tauri::command]
fn get_dummy_assets() -> serde_json::Value {
    let app_dir = match app_dir() {
        Ok(d) => d,
        Err(_) => return serde_json::json!({ "cache_files": [], "log_entries": [] }),
    };

    // cache/ 하위 채널 폴더의 이미지 파일 전체 수집
    let mut cache_files: Vec<String> = Vec::new();
    let cache_dir = app_dir.join("cache");
    if let Ok(channels) = fs::read_dir(&cache_dir) {
        for channel in channels.flatten() {
            if let Ok(files) = fs::read_dir(channel.path()) {
                for file in files.flatten() {
                    let path = file.path();
                    if matches!(path.extension().and_then(|e| e.to_str()), Some("png" | "gif" | "webp")) {
                        cache_files.push(path.to_string_lossy().to_string());
                    }
                }
            }
        }
    }

    // log/ 하위 채널별 최신 .log 파일 파싱
    // 형식: [HH:MM:SS] nickname: message
    //       [HH:MM:SS] [후원] nickname: message
    let mut log_entries: Vec<serde_json::Value> = Vec::new();
    let log_dir = app_dir.join("log");
    if let Ok(channels) = fs::read_dir(&log_dir) {
        for channel in channels.flatten() {
            let mut log_files: Vec<_> = fs::read_dir(channel.path())
                .ok()
                .into_iter()
                .flatten()
                .flatten()
                .filter(|e| e.path().extension().map_or(false, |x| x == "log"))
                .collect();
            log_files.sort_by_key(|e| e.path());

            if let Some(latest) = log_files.last() {
                if let Ok(content) = fs::read_to_string(latest.path()) {
                    for line in content.lines() {
                        // [HH:MM:SS] 이후 부분 추출
                        let Some(rest) = line.strip_prefix('[') else { continue };
                        let Some(after_time) = rest.find("] ") else { continue };
                        let body = &rest[after_time + 2..];

                        let (is_donation, body) = if let Some(r) = body.strip_prefix("[후원] ") {
                            (true, r)
                        } else {
                            (false, body)
                        };

                        if let Some(colon) = body.find(": ") {
                            log_entries.push(serde_json::json!({
                                "nickname": &body[..colon],
                                "message": &body[colon + 2..],
                                "is_donation": is_donation,
                            }));
                        }
                    }
                }
            }
        }
    }

    // 로그는 최신 2000건만
    if log_entries.len() > 2000 {
        let start = log_entries.len() - 2000;
        log_entries = log_entries[start..].to_vec();
    }

    serde_json::json!({
        "cache_files": cache_files,
        "log_entries": log_entries,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(ChatState(Mutex::new(None)))
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            connect_chat,
            disconnect_chat,
            get_settings,
            save_settings,
            get_dummy_assets,
            hide_to_tray,
        ])
        .setup(|app| {
            // 저장된 창 크기·위치 복원
            let dir = app_dir().unwrap_or_else(|_| PathBuf::from("."));
            let saved = settings::load(&dir);

            if let Some(win) = app.get_webview_window("main") {
                // PhysicalSize: 실제 픽셀 단위 (DPI 스케일 적용 전). 고DPI 모니터에서도 정확하게 복원됨
                let _ = win.set_size(tauri::Size::Physical(tauri::PhysicalSize {
                    width: saved.window_width,
                    height: saved.window_height,
                }));
                if let (Some(x), Some(y)) = (saved.window_x, saved.window_y) {
                    // Wayland에서는 set_position이 무시될 수 있음 (compositor가 배치 결정)
                    let _ = win.set_position(tauri::Position::Physical(
                        tauri::PhysicalPosition { x, y },
                    ));
                }

                // X 버튼(CloseRequested)으로 닫을 때 창 상태 저장
                let win_for_close = win.clone();
                let dir_for_close = dir.clone();
                win.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { .. } = event {
                        save_win_state(&win_for_close, &dir_for_close);
                    }
                });
            }

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
                                // 트레이로 숨기기 전에 창 상태 저장
                                if let Ok(dir) = app_dir() {
                                    save_win_state(&win, &dir);
                                }
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
