# ChzzkChatTauri 진행 기록

각 Phase 완료 후 구현 내용과 특이사항을 기록합니다.

---

## Phase 1: Hello World ✅

### 구현 내용

**프로젝트 초기화**
- `npm create tauri-app`으로 Tauri 2 + React + TypeScript 프로젝트 생성
- 주요 의존성: React 19, Vite 7, TypeScript 5.8, @tauri-apps/api 2, @tauri-apps/cli 2

**기본 구조 확인**
- `src/App.tsx`: React 컴포넌트에서 `invoke("greet", { name })` 호출
- `src-tauri/src/lib.rs`: `#[tauri::command] fn greet(name: &str) -> String` 정의
- Tauri IPC(invoke) 기본 동작 확인

### 빌드 환경 검증

**Ubuntu**
- 시스템 의존성: libwebkit2gtk-4.1-dev, build-essential, libssl-dev 등 기설치 확인
- `npm install` 필요 (node_modules 없으면 `tauri: not found` 에러)
- 첫 `npm run tauri dev`: Rust 컴파일 약 1분 18초 (이후 증분 컴파일)
- `npm run tauri build` 성공: .deb (3.9MB), .rpm (3.9MB), .AppImage (75MB)

**Windows**
- 사전 요구사항: Rust(rustup) + Microsoft C++ Build Tools + Node.js
- WebView2는 Windows 10/11 기본 내장
- `target/release/chzzkchattauri.exe` 직접 실행 확인 (배포용은 bundle/ 인하의 installer)

### 참고사항
- Ubuntu → Windows 크로스 컴파일 불가 (WebView2 SDK 의존성 문제)
- Windows 빌드는 Windows 환경에서 직접 실행 필요
- 향후 배포 자동화는 GitHub Actions 사용 예정

---

## Phase 2: 레이아웃 앱 ✅

### 구현 내용

**스타일링: Tailwind CSS v4**
- `npm install -D tailwindcss @tailwindcss/vite`
- `vite.config.ts`에 `tailwindcss()` 플러그인 추가
- `src/index.css`: `@import "tailwindcss"` + 스크롤바 커스텀 + CSS 변수(`--chat-font-size`)
- `src/main.tsx`: `import "./index.css"` 추가

**파일 구조**
```
src/
├── App.tsx                  # 메인 레이아웃 + 상태 관리 (전면 재작성)
├── index.css                # Tailwind + 전역 스타일
├── components/
│   ├── MenuBar.tsx          # 옵션/설정/도움말 드롭다운 메뉴
│   ├── ConnectionBar.tsx    # UID 입력 + 연결/해제 버튼
│   ├── StatusBar.tsx        # 연결 상태 + 메시지 카운트
│   ├── ChatList.tsx         # 스크롤 채팅 목록 (자동 스크롤)
│   └── ChatItem.tsx         # 채팅 아이템 (시간, 닉네임, 메시지)
└── types/
    └── chat.ts              # ChatData 인터페이스 + 색상 상수/유틸
```

**컴포넌트 설계**
- `App.tsx`: 전체 상태 관리 (연결 상태, 채팅 목록, 메뉴 토글)
- `MenuBar.tsx`: hover 기반 드롭다운, 체크 상태 `✓` 표시
- `ConnectionBar.tsx`: 연결 상태에 따라 버튼 green ↔ red 전환, 입력 비활성화
- `StatusBar.tsx`: `ConnectionStatus` 타입별 색상 (yellow/green/red/gray)
- `ChatItem.tsx`: 닉네임 색상(COLOR_CODE_MAP + 해시 팔레트), 후원 금색 배경
- `ChatList.tsx`: `useRef`로 스크롤 컨테이너 참조, `atBottomRef`로 자동 스크롤 잠금

**자동 스크롤 로직**
- `useEffect([chats])`: `atBottomRef.current`가 true일 때만 `scrollTop = scrollHeight`
- `onScroll`: `scrollHeight - scrollTop - clientHeight < 10`이면 맨 아래로 판단
- 사용자가 위로 스크롤하면 자동 스크롤 중단, 맨 아래 도달 시 재개

**색상 상수 (`src/types/chat.ts`)**
- `COLOR_CODE_MAP`: SG001~SG009 프리미엄 색상 9종
- `USER_COLOR_PALETTE`: 일반 유저 12색 팔레트 (uid 문자 합산 해시)
- `getUserColor(uid, colorCode)`: 프리미엄 우선, 없으면 해시 팔레트

### 참고사항
- `npm run tauri dev` 중 React/TypeScript 변경 → Vite 핫 리로드로 즉시 반영 (창 유지)
- Rust 변경 → 자동 재컴파일 후 창 재시작
- `[DEV] 더미 메시지 추가` 버튼으로 자동 스크롤 동작 확인 가능

---

## Phase 3: Rust 백엔드 기초 ✅

### 구현 내용

**의존성 추가 (`Cargo.toml`)**
- `tokio = { version = "1", features = ["full"] }` — 비동기 런타임
- `reqwest = { version = "0.12", features = ["json", "cookies"] }` — HTTP 클라이언트

**파일 구조**
```
src-tauri/src/
├── lib.rs      # Tauri 앱 초기화 + 커맨드 등록 (전면 재작성)
├── api.rs      # Chzzk REST API 호출 (신규)
├── types.rs    # ChatData, Cookies 구조체 (신규)
└── main.rs     # 진입점 (변경 없음)
```

**`types.rs`**
- `ChatData`: 채팅 메시지 구조체 (Phase 4에서 사용 예정)
- `Cookies`: cookies.json 역직렬화용 (`NID_AUT`, `NID_SES`)

**`api.rs`**
- `fetch_channel_name(streamer)` — 채널 이름
- `fetch_chat_channel_id(streamer, cookies)` — 채팅 채널 ID (방송 중일 때만 반환)
- `fetch_access_token(chat_channel_id, cookies)` — (accessToken, extraToken) 튜플
- `fetch_user_id_hash(cookies)` — 사용자 ID 해시
- 모든 함수 `async`, 쿠키는 `Cookie` 헤더로 직접 전달

**`lib.rs` — `connect_chat` 커맨드**
- `load_cookies()`: 실행 파일 옆 → 프로젝트 루트(dev) 순서로 cookies.json 탐색
- `tokio::try_join!`으로 API 병렬 호출 (채널명+채널ID 동시, 액세스토큰+유저해시 동시)
- 반환: `{ channel_name, chat_channel_id, access_token, extra_token, user_id_hash }`

**`App.tsx` 연동**
- `invoke("connect_chat", { streamerUid })` 호출
- 연결 실패 시 에러 메시지 UI에 표시 (빨간 줄)
- URL 파싱 지원: `https://chzzk.naver.com/live/<uid>` 형태 입력 시 UID 자동 추출

### 참고사항
- `mod types;` vs `use types::Cookies;` — mod는 파일 포함, use는 이름 스코프 가져오기
- `tokio::try_join!` — 여러 async 작업을 병렬 실행, 하나라도 실패하면 즉시 Err 반환
- Tauri invoke camelCase ↔ snake_case 자동 변환: `{ streamerUid }` → `streamer_uid: String`
- cookies.json은 `.gitignore`에 추가됨

---
## Phase 4: WebSocket 채팅 수신 ✅

### 구현 내용

**의존성 추가 (`Cargo.toml`)**
- `tokio-tungstenite = { version = "0.26", features = ["native-tls"] }` — WebSocket
- `futures-util = "0.3"` — SinkExt(send), StreamExt(next) 트레이트
- `chrono = { version = "0.4", features = ["clock"] }` — 로컬 시간 포맷

**`chat.rs` (신규)**
- `run()`: 백그라운드 메인 루프. 연결 끊기면 5초 대기 후 채널ID/토큰 재발급 → 재연결.
- `chat_session()`: 한 번의 WebSocket 세션.
  - CONNECT 메시지 전송 → SID 획득
  - 최근 채팅 50건 요청 (응답은 현재 스킵, Phase 5에서 활용 예정)
  - 수신 루프: cmd:0(PING)→cmd:10000(PONG), cmd:93101(채팅), cmd:93102(후원)
  - PING마다 채널ID 재조회 → 변경 시 재연결 (방송 재시작 감지)
- `parse_chat()`: profile(JSON string) 파싱 → nickname, color_code, badges, subscription_month, user_role 추출
- `format_time()`: msgTime(ms) → 로컬 시간 "HH:MM:SS"

**`lib.rs` 변경**
- `ChatState(Mutex<Option<AbortHandle>>)`: 채팅 워커 task 핸들 관리
- `connect_chat`: API 조회 후 `tokio::spawn(chat::run(...))` → AbortHandle 저장
- `disconnect_chat` 커맨드 추가: `handle.abort()`로 워커 중단

**`App.tsx` 변경**
- `useEffect`: `listen("chat-message", ...)` 등록 → chats 상태 업데이트 (최대 10,000건)
- 연결 해제 시 `invoke("disconnect_chat")` 호출

### 참고사항
- WebSocket 자동 ping 없음: tokio-tungstenite는 클라이언트 ping을 자동으로 안 보냄 (Chzzk 서버 호환)
- `AbortHandle`: tokio task를 외부에서 취소하는 핸들. `task.abort_handle()`로 획득, `handle.abort()`로 취소.
- `tauri::State<'_, ChatState>`: Tauri managed state. `.manage()`로 등록, 커맨드 파라미터로 자동 주입.
- 배지 이미지: `<img src={url}>` 직접 로드 (브라우저 메모리 캐시만 적용, 로컬 캐시는 Phase 6)
- 이모지(`{:name:}`) 치환은 Phase 6에서 구현 예정

---

## Phase 5: 채팅 기능 완성 ✅

### 구현 내용

**`settings.rs` (신규)**
- `Settings { font_size: u32, show_timestamp: bool, show_badges: bool, donation_only: bool }`
- `impl Default`: font_size=13, show_timestamp=true, show_badges=true, donation_only=false
- `load(app_dir)`: settings.json 읽기, 실패 시 Default 반환
- `save(app_dir, settings)`: `create_dir_all` + `serde_json::to_string_pretty` → 파일 쓰기

**`lib.rs` 변경**
- `app_dir()` 헬퍼: dev(cookies.json 있는 프로젝트 루트) / 배포(exe 옆 디렉토리)
- `get_settings` 커맨드: `app_dir()`로 settings.json 로드
- `save_settings(s: Settings)` 커맨드: settings.json 저장
- `connect_chat`: log_dir 계산(`app_dir/log/{channel_name}/`) 후 `chat::run`에 전달

**`chat.rs` 변경**
- `run()`, `chat_session()` 파라미터에 `log_dir: PathBuf` 추가
- `write_log(log_dir, chat)`: `log_dir/YYYY-MM-DD.log`에 `[HH:MM:SS] nickname: message` 줄 추가

**`App.tsx` 변경**
- 앱 시작 시 `invoke("get_settings")` 한 번 호출 → 설정 로드
- `settingsRef`: 항상 최신 설정값을 가리키는 ref (stale closure 방지)
- `applySettings(patch)`: `settingsRef.current` 병합 → `invoke("save_settings", { s: next })` 즉시 호출
- 설정 변경 핸들러: `setXxx(next)` + `applySettings(...)` 동시 호출

**`MenuBar.tsx` 변경**
- `fontSize: number` prop + `onFontSizeChange: (size: number) => void` 추가
- 설정 드롭다운에 폰트 크기 +/- 버튼 (범위 10~20) 추가

**`vite.config.ts` 변경**
- `server.watch.ignored`: `**/settings.json`, `**/cookies.json`, `**/log/**` 추가
- 앱이 런타임에 쓰는 파일을 Vite가 감지하여 HMR 리로드 → React 상태 초기화 버그 수정

### 해결한 버그

**설정 저장 시 화면 깜박임 + 채팅 초기화**

원인 탐색 과정:
1. **시도 1** — `setState` 콜백 내에서 `invoke` 호출 → 깜박임 발생
2. **시도 2** — `useEffect([fontSize, showTimestamp, ...])` 자동 저장 → 무한 깜박임
3. **근본 원인** — Vite 파일 워처가 `settings.json` 변경을 감지해 HMR/전체 리로드 → React 상태 소멸

**최종 해결책**: `vite.config.ts`의 `server.watch.ignored`에 런타임 파일 경로 추가.
배포 빌드에는 Vite 워처가 없으므로 dev 전용 문제.

**stale closure 방지**

`useState`의 state는 closure에 갇혀 최신값 보장 불가.
→ `settingsRef`(useRef)로 설정값 미러링하여 항상 최신값 접근.

### 참고사항
- React Strict Mode에서 useEffect가 2회 실행됨 (개발 환경) → auto-save useEffect 방식은 무한 루프 위험
- `settings.json`, `log/` 폴더는 `.gitignore`에 추가 권장
- 로그 파일 경로: `{app_dir}/log/{channel_name}/YYYY-MM-DD.log`

---

## Phase 6: 편의 기능 ✅

### 구현 내용

**`types.rs` 변경**
- `emojis: HashMap<String, String>` 필드 추가 (이모지이름 → 로컬경로 or URL)
- `use std::collections::HashMap` 추가

**`chat.rs` 변경**

`parse_chat()` 개선:
- `extras`를 한 번만 파싱하여 `os_type` + `emojis` 동시 추출 (기존: os_type만 추출)
- Chzzk WebSocket `extras` 필드: `{"osType": "PC", "emojis": {"이름": "URL", ...}}`

이미지 캐시 함수 3개 추가 (외부 crate 불필요):
- `url_to_cache_path(url, cache_dir)`: `DefaultHasher`로 URL 해시 → `{hash:016x}.{ext}` 파일명
- `cache_image(url, cache_dir, client)`: 캐시 파일 있으면 즉시 반환, 없으면 다운로드 후 저장. 실패 시 원본 URL 폴백
- `cache_images(chat, cache_dir, client)`: 모든 배지 + 이모지 URL을 로컬 경로로 교체

흐름:
```
parse_chat() → cache_images() → app_handle.emit("chat-message") → write_log()
```

`run()` / `chat_session()`: `cache_dir: PathBuf` 파라미터 추가. 세션 시작 시 `reqwest::Client` 생성 후 재사용.

**`lib.rs` 변경**
- `cache_dir = app_dir / "cache"` 계산 후 `chat::run`에 전달

**`tauri.conf.json` 변경**
- `assetProtocol.enable: true`, `scope: ["**"]` 추가
- 로컬 파일을 WebView에서 `asset://localhost/절대경로`로 로드 가능하게 설정

**`types/chat.ts` 변경**
- `emojis: Record<string, string>` 추가

**`ChatItem.tsx` 변경**
- `toDisplaySrc(pathOrUrl)`: 로컬 절대경로 → `convertFileSrc()`, 네트워크 URL → 그대로
- `renderMessage(msg, emojis)`: `{:name:}` 패턴 split → 이모지 `<img>` / 일반 텍스트 혼합 반환
  - `msg.split(/\{:(\w+):\}/)` → 홀수 인덱스가 이모지 이름
- `onNicknameClick?: (uid, nickname) => void` prop 추가. 닉네임 클릭 시 유저 필터 트리거.
- 배지 img, 메시지 span에 toDisplaySrc / renderMessage 적용

**`ChatList.tsx` 변경**
- `searchQuery: string`, `selectedUid: string | null`, `onNicknameClick` props 추가
- 필터 스택: donationOnly → selectedUid(`.slice(-500)`) → searchQuery(닉네임+메시지 포함 검색)

**`App.tsx` 변경**
- 검색 상태: `searchQuery`, `showSearch`
- 유저 필터 상태: `selectedUid`, `selectedNickname`
- Ctrl+F: `showSearch` 토글 / Escape: 검색 닫기 (window keydown 리스너)
- `handleNicknameClick`: 같은 uid 재클릭 시 필터 해제 (토글)
- 검색 바 UI (showSearch일 때): autoFocus input + ✕ 버튼
- 유저 필터 바 UI (selectedUid일 때): `👤 닉네임 채팅만 보기` + ✕ 버튼

**`vite.config.ts` 변경**
- `**/cache/**` watch 제외 추가

### 참고사항
- `DefaultHasher`: Rust 표준 라이브러리 해시. 보안용이 아닌 파일명 생성 목적으로 충분
- `convertFileSrc`: `@tauri-apps/api/core`에서 import. 절대경로 → `asset://localhost/...`
- 이모지는 PNG/GIF 모두 지원 (Chzzk 이모지는 주로 WebP/PNG)
- 캐시 경로: `{app_dir}/cache/{channel_name}/` (Phase 7에서 채널별 분리)

---

## Phase 7: 앱 완성도 개선 ✅

### 구현 내용

**앱 아이콘 적용**
- `public/img/chzzk.png` → `bunx tauri icon` 명령으로 모든 사이즈 자동 생성
  - `src-tauri/icons/`: .ico(Windows), .icns(macOS), 다양한 크기 PNG(Linux)
- `MenuBar.tsx`: 메뉴 항목 왼쪽에 `<img src="/img/chzzk.png" className="w-4 h-4">` 추가
  - `public/` 폴더 파일은 Vite에서 `/img/chzzk.png`로 직접 접근 가능

**이미지 캐시 채널별 분리**
- `lib.rs`: `cache_dir` 경로를 `app_dir/cache/{channel_name}/`으로 변경 (기존: `app_dir/cache/`)
- 스트리머별로 이모지/배지 캐시 폴더가 분리됨 → 채널별 캐시 독립 관리 가능

**창 크기/위치 저장 (`tauri-plugin-window-state`)**
- `Cargo.toml`: `tauri-plugin-window-state = "2"` 추가
- `lib.rs`: `.plugin(tauri_plugin_window_state::Builder::default().build())` 등록
- 앱 종료 후 재시작 시 마지막 창 크기/위치 자동 복원 (플러그인이 자동 처리)

**시스템 트레이**
- `Cargo.toml`: `tauri` features에 `"tray-icon"`, `"image-png"` 추가
- `lib.rs` `.setup()` 콜백:
  - `TrayIconBuilder::new().icon(app.default_window_icon()...)` 으로 트레이 아이콘 생성
  - 트레이 좌클릭 → 창이 보이면 숨기기, 숨겨져 있으면 표시+포커스
  - `matches!(win.is_visible(), Ok(true))` 패턴으로 가시성 확인
- `use tauri::Manager` 추가 (get_webview_window 메서드 사용에 필요)
- 닫기(X) = 앱 종료 (기본 동작 유지)
- 트레이 최소화는 메뉴바 버튼으로 명시적 실행 (아래 참고)

**`MenuBar.tsx` 트레이 버튼**
- 설정 드롭다운 우측에 "트레이 아이콘" 독립 버튼 추가
- 클릭 시 `getCurrentWindow().hide()` 호출 → 창 숨김 (트레이에서 좌클릭으로 복원)
- `import { getCurrentWindow } from "@tauri-apps/api/window"` 추가
- 도움말 메뉴: `hidden` 클래스로 숨김 처리 (삭제 예정, DOM에는 유지)

### 참고사항
- `tauri-plugin-window-state`: 별도 코드 없이 플러그인 등록만으로 창 상태 자동 저장/복원
- `app.default_window_icon()`: `tauri.conf.json`의 `bundle.icon` 목록 중 기본 아이콘 반환
- `TrayIconEvent::Click { button: Left, button_state: Up }`: 트레이 좌클릭 업 이벤트
- `getCurrentWindow()`: `@tauri-apps/api/window`에서 import. 현재 WebView 창 인스턴스 반환
- Ubuntu GNOME에서 트레이 아이콘을 보려면 `gnome-shell-extension-appindicator` 설치 필요

---
