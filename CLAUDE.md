# ChzzkChatTauri 개발 가이드

Chzzk 채팅 뷰어를 Tauri(React + TypeScript + Rust)로 처음부터 구현.
Rust와 Tauri를 학습하면서 단계적으로 진행하는 프로젝트.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 19, TypeScript |
| Backend | Rust, Tauri 2 |
| Build | Vite 7, npm |
| IPC | Tauri invoke (Frontend → Backend) |
| IPC | Tauri emit/listen (Backend → Frontend) |

## 개발 단계 로드맵

### Phase 1: Hello World (완료)
- [x] Tauri + React + TypeScript 프로젝트 초기화
- [x] `greet` 커맨드 예제 동작 확인
- [ ] 빌드 및 실행 환경 검증

### Phase 2: 레이아웃 앱
- [ ] 기본 ChatUI 레이아웃 구성 (React 컴포넌트)
  - 상단 입력 영역 (스트리머 UID 입력 + 연결 버튼)
  - 상태 표시 바 (연결 상태, 메시지 카운트)
  - 채팅 목록 영역 (스크롤 가능)
  - 메뉴 바 (옵션, 설정, 도움말)
- [ ] CSS/스타일링 (어두운 테마)
- [ ] 더미 데이터로 채팅 아이템 렌더링
- [ ] 스크롤 동작 구현

### Phase 3: Rust 백엔드 기초
- [ ] HTTP 요청 (reqwest): Chzzk REST API 호출
  - 채팅 채널 ID 조회
  - 채널 이름 조회
  - 액세스 토큰 발급
  - 사용자 ID 해시 조회
- [ ] Tauri 커맨드 → React 데이터 전달
- [ ] 쿠키 파일(cookies.json) 읽기

### Phase 4: WebSocket 채팅 수신
- [ ] Rust WebSocket 클라이언트 (tokio + tokio-tungstenite)
- [ ] Chzzk WebSocket 프로토콜 구현
  - CONNECT → SID 획득 → 최근 채팅 요청
  - PING/PONG 핸들링
  - 채팅/후원 메시지 파싱
- [ ] Tauri Events로 Frontend에 실시간 전달 (`emit`)
- [ ] 재연결 로직 (끊김 감지 → 5초 후 재시도)

### Phase 5: 완전한 ChatUI 구현
- [ ] 채팅 아이템 컴포넌트 (배지, 닉네임 색상, 이모지)
- [ ] 이미지 캐시 (배지/이모지 로컬 저장)
- [ ] 설정 (폰트 크기, 타임스탬프, 배지 표시)
- [ ] 검색 기능 (닉네임/메시지 필터)
- [ ] 후원 강조 표시
- [ ] 유저별 채팅 이력
- [ ] 채팅 로그 파일 기록 (날짜별)

## 프로젝트 구조

```
ChzzkChatTauri/
├── src/                      # React 프론트엔드
│   ├── main.tsx              # React 진입점
│   ├── App.tsx               # 루트 컴포넌트
│   ├── components/           # UI 컴포넌트 (Phase 2~)
│   │   ├── ChatList.tsx
│   │   ├── ChatItem.tsx
│   │   ├── ConnectBar.tsx
│   │   └── StatusBar.tsx
│   └── types/               # TypeScript 타입 정의
│       └── chat.ts
├── src-tauri/               # Rust 백엔드
│   ├── src/
│   │   ├── main.rs          # 진입점
│   │   ├── lib.rs           # Tauri 앱 초기화 + 커맨드 등록
│   │   ├── api.rs           # Chzzk REST API (Phase 3~)
│   │   ├── chat.rs          # WebSocket 채팅 워커 (Phase 4~)
│   │   └── types.rs         # 공유 데이터 구조체
│   └── Cargo.toml
└── package.json
```

## Rust 의존성 계획

```toml
[dependencies]
tauri = { version = "2", features = [] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }     # 비동기 런타임
reqwest = { version = "0.12", features = ["json"] } # HTTP 클라이언트
tokio-tungstenite = "0.24"                          # WebSocket
futures-util = "0.3"                               # Stream 유틸
```

## Tauri IPC 패턴

### Frontend → Backend (invoke)
```typescript
// TypeScript
import { invoke } from "@tauri-apps/api/core";
const result = await invoke("connect_chat", { uid: "streamer_uid" });
```
```rust
// Rust
#[tauri::command]
async fn connect_chat(uid: String) -> Result<String, String> {
    // ...
}
```

### Backend → Frontend (event emit)
```rust
// Rust: 채팅 메시지 전송
app_handle.emit("chat-message", &chat_data).unwrap();
```
```typescript
// TypeScript: 수신
import { listen } from "@tauri-apps/api/event";
await listen<ChatData>("chat-message", (event) => {
  setChatList(prev => [...prev, event.payload]);
});
```

## Chzzk 채팅 데이터 구조 (Rust)

```rust
#[derive(Serialize, Deserialize, Clone)]
pub struct ChatData {
    pub time: String,
    pub chat_type: String,   // "채팅" | "후원"
    pub uid: String,
    pub nickname: String,
    pub message: String,
    pub color_code: String,
    pub badges: Vec<String>, // 이미지 URL 목록
    pub subscription_month: u32,
    pub os_type: String,     // "PC" | "MOBILE"
    pub user_role: String,   // "common_user" | "manager" | "streamer"
}
```

## 레퍼런스 소스 (Flet 구현)

Tauri 구현 시 참고할 Flet 소스:
- `../ChzzkChat/src/api.py` — REST API 호출 로직
- `../ChzzkChat/src/chat_worker.py` — WebSocket 연결 및 메시지 파싱
- `../ChzzkChat/src/main.py` — UI 구성 및 이벤트 처리
- `../ChzzkChat/src/cmd_type.py` — WebSocket 명령어 상수

## 개발 명령어

```bash
# 개발 서버 실행
npm run tauri dev

# 빌드
npm run tauri build

# TypeScript 타입 체크
npx tsc --noEmit
```

## 주요 주의사항

1. **WebSocket ping**: Chzzk 서버는 클라이언트 WebSocket ping에 응답하지 않음.
   tokio-tungstenite에서 자동 ping 비활성화 필요.

2. **PING/PONG**: 서버가 cmd:0(ping) 보내면 cmd:10000(pong)으로 응답해야 연결 유지.

3. **비동기 처리**: WebSocket은 별도 tokio task로 실행, Tauri emit으로 UI 업데이트.

4. **메모리 관리**: 채팅 최대 10,000건 유지 (초과 시 오래된 것 제거).
