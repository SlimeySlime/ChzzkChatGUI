# ChzzkChatTauri 개발 가이드

Chzzk 채팅 뷰어를 Tauri(React + TypeScript + Rust)로 처음부터 구현.
Rust와 Tauri를 학습하면서 단계적으로 진행하는 프로젝트.

**현재 단계: Phase 7 완료 (나중에 항목 대기 중)**

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 19, TypeScript |
| Backend | Rust, Tauri 2 |
| Build | Vite 7, npm |
| IPC (FE→BE) | `invoke` (단발 요청/응답) |
| IPC (BE→FE) | `emit` / `listen` (실시간 이벤트) |

## 프로젝트 구조

```
ChzzkChatTauri/
├── src/                      # React 프론트엔드
│   ├── main.tsx              # React 진입점
│   ├── App.tsx               # 루트 컴포넌트
│   ├── components/           # UI 컴포넌트
│   └── types/                # TypeScript 타입 정의
├── src-tauri/                # Rust 백엔드
│   ├── src/
│   │   ├── main.rs           # 진입점
│   │   ├── lib.rs            # Tauri 앱 초기화 + 커맨드 등록
│   │   ├── api.rs            # Chzzk REST API
│   │   ├── chat.rs           # WebSocket 채팅 워커
│   │   └── types.rs          # 공유 데이터 구조체
│   └── Cargo.toml
└── package.json
```

## Tauri IPC 패턴

### Frontend → Backend (invoke)
```typescript
import { invoke } from "@tauri-apps/api/core";
const result = await invoke("connect_chat", { uid: "streamer_uid" });
```
```rust
#[tauri::command]
async fn connect_chat(uid: String) -> Result<String, String> { ... }
```

### Backend → Frontend (emit/listen)
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
    pub chat_type: String,        // "채팅" | "후원"
    pub uid: String,
    pub nickname: String,
    pub message: String,
    pub color_code: String,
    pub badges: Vec<String>,      // 이미지 URL 목록 (최대 3개)
    pub subscription_month: u32,
    pub os_type: String,          // "PC" | "MOBILE"
    pub user_role: String,        // "common_user" | "manager" | "streamer"
}
```

## 레퍼런스 소스 (Flet 구현)

| 파일 | 참고 내용 |
|------|----------|
| `../ChzzkChat/src/api.py` | REST API 호출 로직 |
| `../ChzzkChat/src/chat_worker.py` | WebSocket 연결 및 메시지 파싱 |
| `../ChzzkChat/src/main.py` | UI 구성 및 이벤트 처리 |
| `../ChzzkChat/src/cmd_type.py` | WebSocket 명령어 상수 |

## 개발 명령어

```bash
npm install          # 첫 설치 시
npm run tauri dev    # 개발 서버 (Rust + React 핫리로드)
npm run tauri build  # 배포 빌드
```

## 주요 주의사항

1. **WebSocket ping**: Chzzk 서버는 클라이언트 WebSocket ping에 응답하지 않음.
   tokio-tungstenite 자동 ping 비활성화 필요 (`ping_interval: None`).

2. **PING/PONG**: 서버 cmd:0(ping) → 클라이언트 cmd:10000(pong) 응답 필수.

3. **비동기 처리**: WebSocket은 별도 tokio task로 실행, Tauri emit으로 UI 업데이트.

4. **메모리 관리**: 채팅 최대 10,000건 유지 (초과 시 오래된 것 제거).
