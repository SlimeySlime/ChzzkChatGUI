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

## 버그 수정 및 개선 (Phase 7 이후)

### Windows 환경 설정 수정

**문제**: Ubuntu에서 커밋된 프로젝트를 Windows에서 실행 시 `bun`을 찾을 수 없다는 오류 발생

**원인**: `tauri.conf.json`의 `beforeDevCommand` / `beforeBuildCommand`가 `bun run dev/build`로 설정되어 있었으나 Windows에 bun 미설치

**해결**: `tauri.conf.json`에서 `bun` → `npm`으로 변경

---

### 이모지 메모리 누수 수정 (`chat.rs`)

**문제**: 장시간(1시간+) 연결 시 WebView out of memory 발생. 더미 데이터(배지/이모지 없음)로는 재현 안 됨.

**원인**: Chzzk WebSocket API는 `extras.emojis`에 채널 이모지 세트 전체(수십~수백 개)를 매 메시지마다 전송함. 기존 코드는 이를 필터링 없이 각 ChatData에 저장했고, `cache_images()`가 사용하지 않는 이모지 이미지까지 전부 다운로드 및 캐시.

메시지 수 × 채널 이모지 수 = JS 힙 폭증 (20,000건 × 100이모지 = 수백 MB)

**해결** (`parse_chat`): 메시지 텍스트에서 `{:name:}` 패턴을 먼저 추출, 실제 사용된 이모지만 emojis 맵에 보존. 미사용 이모지는 폐기.

```
사용 전: 채널 이모지 전체 (100개) × 모든 메시지
사용 후: 메시지에 실제 쓰인 이모지만 (0~3개)
```

---

### 더미 테스트 데이터 개선 (`lib.rs`, `App.tsx`)

**문제**: 기존 더미 데이터는 `badges: []`, `emojis: {}`로 생성되어 실제 이미지 메모리 동작을 테스트할 수 없었음

**해결**:
- `get_dummy_assets` Tauri 커맨드 추가: 실제 `cache/` 이미지 파일 경로 목록 + `log/` 파싱 결과(닉네임·메시지·후원 여부) 반환
- `App.tsx`: 앱 시작 시 `get_dummy_assets` 호출. 로그에서 실제 사용된 이모지 이름 추출 → 캐시 파일에 round-robin 매핑
- 더미 메시지에 실제 캐시 이미지(배지 0~2개)와 전체 이모지맵 포함 → 실제 API 동작과 동일한 메모리 환경 재현 가능

---

### 버그 수정: 트레이 아이콘 버튼 무동작

**원인**: Tauri v2에서 프론트엔드의 `getCurrentWindow().hide()` 호출은 capability 권한 필요. `capabilities/default.json`에 `core:window:allow-hide`가 누락되어 있어 버튼 클릭이 무시됨 (Rust 측 트레이 이벤트 핸들러는 서버 사이드라 권한 불필요).

**해결**: `capabilities/default.json`에 `"core:window:allow-hide"` 추가

---

### 버그 수정: 빠른 채팅 수신 시 자동 스크롤 멈춤 (`ChatList.tsx`)

**현상**: 채팅이 빠르게 올라올 때 스크롤이 최하단에 있어도 새 메시지를 따라가지 않고 고정됨

**원인**: `scrollTop = scrollHeight` 대입이 브라우저의 scroll 이벤트를 동기적으로 발생시킴. `handleScroll`이 이 이벤트를 받아 `atBottomRef`를 계산하는데, 이 시점에 브라우저 레이아웃이 아직 새 항목 높이를 반영하기 전일 수 있어 `scrollHeight - scrollTop - clientHeight > 10` 조건을 만족 → `atBottomRef = false`로 잘못 설정.

이후 메시지 도착 시 `atBottomRef`가 `false`이므로 스크롤을 시도하지 않아 고정된 상태 지속.

**해결**:
- `isProgrammaticRef` 플래그 추가: 코드가 직접 스크롤하는 동안 발생하는 scroll 이벤트를 `handleScroll`이 무시하도록 함
- `setTimeout(0)`으로 scroll 이벤트 처리 후 플래그 해제
- 하단 판정 임계값을 10px → 50px로 완화 (빠른 렌더링 중 미세한 오차 허용)

---

## Phase 8: 가상 스크롤 ✅

### 배경

장시간 실행 시 WebView2 메모리가 수 GB까지 증가하는 근본 원인 분석:
- **이모지 맵 수정**(Phase 7 후)으로 JS 힙 문제는 해결됐으나, 메모리 증가 지속
- `채팅 초기화`(setChats([])) 후에도 메모리가 거의 줄지 않음 → 원인이 React state가 아님
- 원인: **Chromium 이미지 디코드 캐시** — `<img>` DOM 요소가 제거돼도 캐시는 유지됨
- 10,000개 ChatItem이 DOM에 상주 → 각 배지/이모지 `<img>` 태그의 디코드 캐시가 누적
- WebView2는 임베드 컴포넌트 특성상 OS 메모리 압박 신호를 제대로 받지 못해 캐시 미해제
- 스트림 시간이 길어질수록 새로운 고유 사용자 → 새로운 배지 이미지 → 캐시 단조 증가

### 해결 원리

가상 스크롤: 전체 항목 수와 무관하게 **뷰포트에 보이는 항목만 DOM에 유지**

```
기존: 10,000개 <img> DOM 상주 → 10,000개 디코드 캐시 항목 보유
가상: ~30개 <img>만 DOM 존재 → 뷰포트 밖 항목 DOM 제거 → Chromium 캐시 해제 가능
```

### 구현 내용

**의존성 추가**
- `@tanstack/react-virtual` — React 가상 스크롤 라이브러리

**`ChatList.tsx` 전면 재작성**

- `useVirtualizer({ count, getScrollElement, estimateSize, overscan })` 적용
  - `estimateSize: () => 28` — 초기 추정 높이 (실제 높이는 measureElement가 측정)
  - `overscan: 10` — 뷰포트 위아래 10개 추가 렌더링 (빠른 스크롤 시 공백 방지)
- 렌더링 구조: 전체 높이를 가진 `position: relative` 컨테이너 + 각 항목 `position: absolute`
  - 스크롤바가 전체 콘텐츠 길이를 정확히 반영하면서 DOM 노드는 최소로 유지
- `virtualizer.measureElement` ref: 가변 높이 아이템(이모지, 긴 메시지 등) 실측
- 자동 스크롤: 기존 `isProgrammaticRef` 패턴 유지, `scrollTop` 직접 조작 대신 `virtualizer.scrollToIndex` 사용
- 필터 로직(donationOnly, selectedUid, searchQuery) 변경 없음

**`ChatItem.tsx`**
- `memo()` 래핑: props가 변경되지 않은 항목의 불필요한 재렌더링 방지
  - 가상 스크롤 환경에서 새 메시지 추가 시 기존 표시 항목이 재렌더링되지 않음

### 효과

| | 이전 | 이후 |
|---|---|---|
| DOM 내 ChatItem 수 | 최대 10,000개 | 뷰포트 크기에 따라 ~30~50개 |
| 활성 `<img>` 요소 수 | ~15,000개 (배지 포함) | ~50~150개 |
| 장시간 메모리 증가 | 수 GB 단조 증가 | 안정적 유지 |
| 스크롤 전체 항목 탐색 | ✓ | ✓ (변경 없음) |

### 참고사항
- `useVirtualizer`는 `count`가 변경될 때 내부 상태를 재계산하므로, 필터 결과 배열의 길이 변화를 자동으로 추적함
- `measureElement` ref callback은 각 항목이 DOM에 마운트될 때 실제 높이를 측정하여 `estimateSize`의 오차를 보정
- 가상 스크롤 적용 후 맨 위로 스크롤해도 이전 메시지 탐색 가능 (전체 항목은 state에 유지, DOM만 가상화)

---

## Phase 9: 버그 수정 ✅

### 버그 1: 메뉴바 드롭다운 재클릭 시 안 닫힘

**원인**: `index.css`의 `.menu-dropdown:hover`/`:focus-within` CSS만으로 드롭다운을 제어하고 있었음. 버튼 클릭 후 포커스가 유지되면 `:focus-within` 조건이 계속 참이라 재클릭해도 닫히지 않음.

**왜 CSS만으로는 불가능한가**: "재클릭 닫기 + 외부 클릭 닫기 + 다른 메뉴 열면 현재 닫기" 세 조건을 동시에 만족하려면 JS(React state)가 필수. CSS는 클릭 상태를 기억하지 못함.

**해결** (`MenuBar.tsx`):
- `openMenu: string | null` state 추가
- `toggle(name)`: 같은 메뉴 재클릭 → `null`, 다른 메뉴 클릭 → 전환
- `handleAction(fn)`: 메뉴 항목 클릭 시 액션 실행 + `setOpenMenu(null)`
- `menuBarRef` + `mousedown` 이벤트로 외부 클릭 감지 → 닫힘
- `{openMenu === "options" && <div>...}` 조건부 렌더링으로 전환

**해결** (`index.css`):
- `.menu-dropdown:focus-within .menu-panel`, `.menu-dropdown:hover .menu-panel` 규칙 제거
- `.menu-panel`의 `display: none` 제거 (조건부 렌더링으로 대체)

---

### 버그 2: 빌드 `.exe` 실행 시 log/cache 경로 오동작

**원인**: `app_dir()`이 런타임에 `cookies.json` 존재 여부로 dev/prod를 구분하고 있었음. release 빌드된 `.exe`도 `src-tauri/target/release/` 경로에서 실행하면 4단계 위가 프로젝트 루트이고 거기에 `cookies.json`이 있으면 프로젝트 루트를 사용함. NSIS 설치 후 `AppData\Local\...`에서 실행하면 `ancestors().nth(4)` = 유저 홈 디렉토리로 올라가버려 cookies.json 미발견 → exe 옆(AppData)으로 폴백 → 사용자가 로그 위치를 못 찾음.

**해결** (`lib.rs`):
```rust
fn app_dir() -> Result<PathBuf, String> {
    let exe = std::env::current_exe()?;
    #[cfg(debug_assertions)]
    { /* 프로젝트 루트 (4단계 위) */ }
    // release: exe 옆 (포터블 방식)
    exe.parent().map(|p| p.to_path_buf())...
}
```
- `cfg!(debug_assertions)`: 컴파일 타임에 debug/release 분기 → 런타임 경로 탐색 불필요
- release 빌드는 exe를 어디에 두든 항상 exe 옆 디렉토리 사용 (포터블)
- `load_cookies()`도 `app_dir()` 기반으로 단순화 (기존: 후보 경로 복수 탐색)

---

### 창 크기·위치: `tauri-plugin-window-state` → `settings.json` 통합

**배경**: 플러그인은 Linux Wayland에서 위치 복원 불가 (`set_position()` compositor가 무시), 상태 파일도 AppData에 별도 저장되어 포터블 방식과 맞지 않음.

**`settings.rs` 변경**:
- `window_width: u32`, `window_height: u32`, `window_x: Option<i32>`, `window_y: Option<i32>` 추가
- **중요**: 새 필드에 `#[serde(default)]` 필수. 없으면 기존 settings.json(새 필드 없음) 역직렬화 실패 시 `unwrap_or_default()`로 폴백되어 font_size 등 기존 설정 전체가 초기화됨.

**`lib.rs` 변경**:
- `save_win_state(win, dir)` 헬퍼: `inner_size()` 저장, `outer_position()`은 실패(Wayland) 시 건너뜀
- 저장 시점 3곳:
  1. X 버튼 → `on_window_event(CloseRequested)`
  2. "트레이 아이콘" 버튼 → `hide_to_tray` 커맨드 (저장 후 `win.hide()`)
  3. 트레이 아이콘 클릭 숨기기 → tray handler 내 `save_win_state` 호출
- `setup()`: `PhysicalSize`/`PhysicalPosition`으로 저장된 크기·위치 복원
- `hide_to_tray` 커맨드 추가 및 `invoke_handler`에 등록

**`MenuBar.tsx` 변경**:
- `getCurrentWindow().hide()` → `invoke("hide_to_tray")`
- 직접 `hide()`하면 저장 없이 숨겨지므로 Rust 커맨드 경유 필수

**`Cargo.toml` 변경**:
- `tauri-plugin-window-state = "2"` 제거

**플랫폼별 동작**:
| 환경 | 크기 복원 | 위치 복원 |
|------|---------|---------|
| Windows | ✅ | ✅ |
| Linux X11 | ✅ | ✅ |
| Linux Wayland | ✅ | ❌ (compositor가 배치 결정, 저장은 됨) |

---

## Phase 10: 다크/라이트 테마 전환 ✅

### 설계 결정

**Tailwind `dark:` prefix 미사용** → CSS 변수 + `data-theme` 속성 방식 채택.

이유:
- `dark:` prefix는 dark/light 2가지만 지원. 향후 커스텀 테마 확장 시 구조 재설계 필요.
- CSS 변수 방식은 `[data-theme="xxx"]` 셀렉터만 추가하면 테마 무한 확장 가능.
- 컴포넌트 JSX에 `dark:` prefix 없이 단일 클래스명(`bg-theme-primary`)만 쓰면 됨.

### 구현 내용

**`src/index.css`**

테마별 CSS 변수 정의:
```css
[data-theme="dark"]  { --bg-primary: #171717; --text-primary: #ffffff; ... }
[data-theme="light"] { --bg-primary: #f0f0f0; --text-primary: #0a0a0a; ... }
```

변수 목록:
| 변수 | 용도 |
|------|------|
| `--bg-primary` | 메인 배경 (neutral-900 계열) |
| `--bg-secondary` | 서브 배경 (neutral-800 계열) |
| `--bg-tertiary` | 3차 배경 (neutral-700 계열, hover 대상) |
| `--bg-deep` | 가장 어두운 배경 (neutral-950 계열) |
| `--text-primary` | 주 텍스트 |
| `--text-secondary` | 보조 텍스트 |
| `--text-muted` | 흐린 텍스트 (타임스탬프, 카운트 등) |
| `--border` | 경계선 |
| `--scrollbar` / `--scrollbar-hover` | 스크롤바 색상 |
| `--donation-bg` | 후원 메시지 배경 |

Tailwind v4 `@utility` 디렉티브로 유틸리티 클래스 등록:
```css
@utility bg-theme-primary   { background-color: var(--bg-primary); }
@utility text-theme-muted   { color: var(--text-muted); }
@utility border-theme       { border-color: var(--border); }
@utility placeholder-theme-muted { &::placeholder { color: var(--text-muted); } }
```
→ `hover:bg-theme-tertiary`, `focus:border-theme` 등 Tailwind 변형 자동 지원

**`src-tauri/src/settings.rs`**
- `theme: String` 필드 추가 (기본값: `"dark"`)
- `#[serde(default = "default_theme")]` 필수 — 기존 settings.json 호환성 유지

**`src/App.tsx`**
- `theme` state 추가 (기본값 `"dark"`)
- 설정 로드 시 `s.theme ?? "dark"` 적용
- `useEffect([theme])`: `document.documentElement.setAttribute("data-theme", theme)` — DOM에 반영
- `settingsRef`에 `theme` 필드 추가 → `applySettings({ theme: t })` 로 저장
- MenuBar에 `theme`, `onThemeChange` props 전달

**`src/components/MenuBar.tsx`**
- `theme: string`, `onThemeChange: (theme: string) => void` props 추가
- 설정 드롭다운 하단에 토글 버튼:
  - dark일 때 → "라이트 모드" 표시
  - light일 때 → "다크 모드" 표시

**전체 컴포넌트 색상 교체**

| 기존 Tailwind 클래스 | 교체 후 |
|---------------------|---------|
| `bg-neutral-900/950` | `bg-theme-primary` / `bg-theme-deep` |
| `bg-neutral-800` | `bg-theme-secondary` |
| `bg-neutral-700` | `bg-theme-tertiary` |
| `text-white`, `text-neutral-100` | `text-theme-primary` |
| `text-neutral-200/300` | `text-theme-secondary` |
| `text-neutral-400/500` | `text-theme-muted` |
| `border-neutral-700/600` | `border-theme` |
| `hover:bg-neutral-700/600` | `hover:bg-theme-tertiary` |

고정 색상 (테마 미적용):
- 연결 상태: `text-green-400`, `text-yellow-400`, `text-red-400` (시맨틱 색상)
- 연결/해제 버튼: `bg-green-700`, `bg-red-600`
- 에러 메시지: `bg-red-950 text-red-400`

### 참고사항
- `[data-theme]` 셀렉터는 `:root` 변수보다 specificity가 높아 기본값 override 필요 없음
- `@utility`로 정의한 커스텀 클래스는 Tailwind v4에서 `hover:`, `focus:` 등 변형 자동 지원
- `data-theme`은 `<html>` 요소에 설정 — 하위 모든 CSS 변수가 cascading으로 적용됨

---

## Phase 11: 여러 스트리머 동시 모니터링 (탭) ✅

### 설계 결정

탭 최대 5개 제한. 탭별 독립적인 채팅 스트림, 검색, 유저 필터.
전역 설정(폰트 크기, 테마, 타임스탬프 등)은 모든 탭 공유.

워커 동시 실행 성능 검토:
- 각 탭 = 독립 tokio task(경량 비동기 스레드) + WebSocket 연결 1개
- 5탭 동시 연결 시 약 5개 WebSocket, CPU/메모리 영향 미미 (I/O 바운드)
- 기존 단일 `Option<AbortHandle>` → `HashMap<String, AbortHandle>` 최소 변경으로 지원

### 구현 내용

**`src/types/tab.ts` (신규)**
```typescript
export interface Tab {
  tabId: string;
  uid: string;             // 입력 필드값 (URL 또는 uid)
  streamerUid: string;     // 연결된 실제 streamer uid
  channelName: string;
  status: ConnectionStatus;
  errorMsg: string;
  chats: ChatData[];
  searchQuery: string;
  showSearch: boolean;
  selectedUid: string | null;
  selectedNickname: string;
}
export const MAX_TABS = 5;
export function newTab(): Tab { ... }
```

**`src/components/TabBar.tsx` (신규)**
- 탭마다 `●` 연결 상태 표시 (green=connected, muted=idle)
- 채널 이름 또는 "새 탭", `max-w-28 truncate`로 오버플로우 처리
- ✕ 닫기 버튼 (탭이 2개 이상일 때만 표시), ＋ 추가 버튼 (5개 미만일 때만 표시)
- MenuBar 하단 배치

**`src/App.tsx` 전면 재작성**
- 단일 상태 → `tabs: Tab[]` + `activeTabId: string` 배열 상태로 전환
- `updateTab(tabId, patch)`: 단일 업데이터 함수로 모든 탭 상태 수정 통일
- `addTab()`, `closeTab(tabId)`: 탭 추가/삭제 (닫힌 탭이 활성 탭이면 인접 탭으로 전환)
- `connectTab(tabId, uid)`: per-tab `listen("chat-message-{streamerUid}", ...)` 등록
- `disconnectTab(tabId, streamerUid)`: invoke + 리스너 해제 + 탭 상태 초기화
- `unlistenMap = useRef<Map<string, () => void>>(new Map())`: 탭별 이벤트 리스너 해제 함수 저장
- `activeTabIdRef`: keydown 핸들러 등 closure에서 최신 activeTabId 참조용
- DEV 스트레스 테스트: 시작 시 `targetTabId` 캡처 → 탭 전환 후에도 해당 탭에만 더미 메시지

**`src-tauri/src/lib.rs` 변경**
- `ChatState`: `Mutex<Option<AbortHandle>>` → `Mutex<HashMap<String, AbortHandle>>`
- `.manage()`: `Mutex::new(None)` → `Mutex::new(HashMap::new())`
- `connect_chat`: `.take()` → `.remove(&streamer_uid)` (기존 연결 중단), `.insert(streamer_uid.clone(), ...)` (새 핸들 저장)
- `disconnect_chat`: `streamer_uid: String` 파라미터 추가, `.take()` → `.remove(&streamer_uid)`

**`src-tauri/src/chat.rs` 변경**
- `app_handle.emit("chat-message", &chat)` → `app_handle.emit(&format!("chat-message-{streamer_uid}"), &chat)`
- `streamer_uid`는 이미 `chat_session()` 파라미터로 존재 → 변경 최소

### 참고사항
- `unlistenMap`을 `useRef<Map>` (ref of Map)으로 관리: state에 넣으면 listen 등록마다 리렌더링 발생
- `activeTabIdRef`는 keydown 이벤트 핸들러 closure의 stale capture 방지용. `useEffect([], [])` 내 등록된 핸들러는 초기 `activeTabId` 값에 고정되므로 ref를 통해 최신값 참조 필요
- 이벤트명 `chat-message-{uid}`: 탭이 같은 채널에 중복 연결 시 동일 이벤트를 두 탭이 모두 수신하는 문제 있음 → 현재는 connect 시 기존 워커 abort로 단일 연결 보장

---

## Phase 12: 배포 자동화 🚧 진행 중

### 현재 상태
- v0.4.0 빌드 중 (`.sig` + `latest.json` 생성 확인 예정)
- v0.5.0 배포 후 v0.4.0 앱에서 자동 업데이트 동작 검증 예정

### 서명 키 트러블슈팅

초기에 `--ci` 플래그로 생성한 키는 빈 비밀번호로 서명이 동작하지 않았음.
→ `.sig` 파일 미생성 → `latest.json` 미생성 → 업데이터 동작 불가

**해결**: `--password "PASSWORD"` 로 비밀번호를 명시해서 재생성.
로컬 서명 테스트(`signer sign`)로 `.sig` 생성 확인 후 적용.

```bash
# 올바른 키 생성 방법
npm run tauri -- signer generate -w ~/notes/keys/tauri_key --password "PASSWORD"

# 로컬 서명 테스트
npm run tauri -- signer sign -k "$(cat ~/notes/keys/tauri_key)" -p "PASSWORD" /tmp/test.txt
# → /tmp/test.txt.sig 생성되면 성공
```

GitHub Secrets 필수 2개:
- `TAURI_SIGNING_PRIVATE_KEY`: 비밀키 파일 내용
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: 키 생성 시 사용한 비밀번호

### 서명 키 구조

Tauri 업데이터는 **ed25519 서명**으로 배포 파일 위변조를 검증한다.

```
npm run tauri -- signer generate -w <path> --password "PASSWORD"
  → 비밀키(private key): GitHub Secrets에 저장 (TAURI_SIGNING_PRIVATE_KEY)
  → 공개키(public key): tauri.conf.json plugins.updater.pubkey에 저장 (커밋 OK)
```

빌드 시 Actions에서 비밀키로 서명 → 앱 실행 시 공개키로 서명 검증 → 위변조 방지.

### `.github/workflows/release.yml`

`v*` 태그 push 시 Ubuntu + Windows 병렬 빌드 후 GitHub Release Draft 자동 생성.

```
git tag v0.2.0 && git push origin v0.2.0
  → Actions 자동 실행
  → Ubuntu: .deb, .AppImage 빌드
  → Windows: .exe, .msi 빌드
  → latest.json 생성 (업데이터 메타데이터)
  → GitHub Release Draft에 모든 파일 업로드
  → Draft → Publish 후 latest endpoint 활성화
```

**주요 설정:**
- `fail-fast: false`: 한 플랫폼 실패해도 나머지 계속
- `releaseDraft: true`: 자동 공개 방지, 릴리즈 노트 작성 후 수동 Publish
- `includeUpdaterJson: true`: `latest.json` 자동 생성 및 첨부
- `swatinem/rust-cache`: `src-tauri/target/` 캐시로 빌드 시간 단축

### `tauri.conf.json` 업데이터 설정

```json
"plugins": {
  "updater": {
    "pubkey": "...(공개키)...",
    "endpoints": [
      "https://github.com/SlimeySlime/ChzzkChatGUI/releases/latest/download/latest.json"
    ]
  }
}
```

엔드포인트의 `releases/latest`는 **Published 릴리즈** 중 가장 최신을 가리킨다. Draft 상태면 감지 안 됨.

### `App.tsx` 업데이트 UI

앱 시작 시 1회 `check()` 호출 → 새 버전이면 상단에 파란 배너 표시:

```tsx
// 앱 시작 시 체크
check().then((update) => {
  if (update?.available) setUpdateAvailable({ version, body });
}).catch(() => {}); // 오프라인 시 무시

// UI: 파란 배너 + "지금 업데이트" 버튼
await update.downloadAndInstall();
await relaunch(); // tauri-plugin-process
```

### 의존성 추가

**Cargo.toml:**
```toml
tauri-plugin-updater = "2"
tauri-plugin-process = "2"  # relaunch() 제공
```

**package.json:**
```
@tauri-apps/plugin-updater
@tauri-apps/plugin-process
```

**capabilities/default.json:**
```json
"updater:default",
"process:allow-restart"
```

### 릴리즈 버전 올리는 법

세 파일 버전을 동일하게 맞춰야 한다:
- `tauri.conf.json`: `"version": "0.3.0"`
- `Cargo.toml`: `version = "0.3.0"`
- `package.json`: `"version": "0.3.0"`

```bash
git add . && git commit -m "bump version to 0.3.0"
git push
git tag v0.3.0
git push origin v0.3.0
```

### dev 환경에서 테스트 불가

`npm run tauri dev`는 debug 빌드라 업데이터 비활성화됨. 실제 자동 업데이트는 release 빌드된 앱에서만 동작. UI 확인만 하려면 App.tsx에서 `setUpdateAvailable` 임시 강제 호출로 배너 확인 가능.

### 참고사항
- `latest.json` 엔드포인트: `releases/latest` = Published 릴리즈 기준. Draft는 미포함.
- 비밀키 분실 시 업데이터 서명 불가 → 별도 보관 필수.
- 태그명(`v0.3.0`)과 `tauri.conf.json` 버전(`0.3.0`) 앞에 `v` 유무만 다른 형태로 일치해야 버전 비교가 정상 동작.
