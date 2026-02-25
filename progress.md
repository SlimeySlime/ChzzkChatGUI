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
- 배지 이미지: `<img src={url}>` 직접 로드 (브라우저 메모리 캐시만 적용, 로컬 캐시는 Phase 5)
- 이모지(`{:name:}`) 치환은 Phase 5에서 구현 예정

---
