# ChzzkChatTauri 개발 체크리스트

## Phase 1: Hello World ✅
- [x] Tauri + React + TypeScript 프로젝트 초기화
- [x] `greet` 커맨드 예제 동작 확인
- [x] Ubuntu 개발 서버(`npm run tauri dev`) 실행 확인
- [x] Ubuntu 빌드(`npm run tauri build`) 확인 (.deb, .rpm, .AppImage)
- [x] Windows 빌드 및 exe 실행 확인

## Phase 2: 레이아웃 앱 ✅
- [x] 기본 ChatUI 레이아웃 구성 (React 컴포넌트)
  - [x] 상단 입력 영역 (스트리머 UID 입력 + 연결 버튼)
  - [x] 상태 표시 바 (연결 상태, 메시지 카운트)
  - [x] 채팅 목록 영역 (스크롤 가능한 ListView)
  - [x] 메뉴 바 (옵션, 설정, 도움말)
- [x] CSS/스타일링 (어두운 테마, Tailwind CSS v4)
- [x] 더미 데이터로 채팅 아이템 렌더링
- [x] 자동 스크롤 동작 구현 (사용자 스크롤 시 잠금)

## Phase 3: Rust 백엔드 기초 ✅
- [x] Cargo.toml에 reqwest, tokio 추가
- [x] `api.rs` — Chzzk REST API 호출
  - [x] 채팅 채널 ID 조회
  - [x] 채널 이름 조회
  - [x] 액세스 토큰 발급
  - [x] 사용자 ID 해시 조회
- [x] `types.rs` — 공유 데이터 구조체 정의
- [x] Tauri 커맨드로 React에 데이터 전달 (`connect_chat`)
- [x] cookies.json 파일 읽기 (실행 파일 옆 또는 프로젝트 루트 자동 탐색)

## Phase 4: WebSocket 채팅 수신 ✅
- [x] Cargo.toml에 tokio-tungstenite, chrono, futures-util 추가
- [x] `chat.rs` — WebSocket 채팅 워커
  - [x] CONNECT → SID 획득 → 최근 채팅 50건 요청
  - [x] PING/PONG 핸들링 (cmd:0 → cmd:10000)
  - [x] 채팅(93101) / 후원(93102) 메시지 파싱
- [x] Tauri emit으로 프론트엔드에 실시간 전달 (`chat-message` 이벤트)
- [x] 재연결 로직 (끊김 감지 → 5초 대기 후 채널ID/토큰 재발급 → 재연결)
- [x] `disconnect_chat` 커맨드 (AbortHandle로 워커 중단)

## Phase 5: 완전한 ChatUI 구현
- [ ] 닉네임 색상 (color_code 기반, 해시 팔레트)
- [ ] 배지 이미지 렌더링 (최대 3개)
- [ ] 이모지 치환
  - [ ] `types.rs`: ChatData에 `emojis: HashMap<String, String>` 필드 추가
  - [ ] `chat.rs`: extras에서 emojis 파싱 후 ChatData에 포함
  - [ ] `ChatItem.tsx`: `{:name:}` 패턴을 `<img>` 태그로 렌더링
- [ ] 이미지 캐시 (배지/이모지 로컬 저장, MD5 해시 파일명)
- [ ] 후원 메시지 강조 표시 (배경색)
- [ ] 검색 기능 (Ctrl+F, 닉네임/메시지 필터)
- [ ] 후원만 보기 토글
- [ ] 유저별 채팅 이력 (닉네임 클릭)
- [ ] 설정 (폰트 크기, 타임스탬프, 배지 표시)
- [ ] 채팅 로그 파일 기록 (log/{channel}/YYYY-MM-DD.log)
- [ ] 메모리 관리 (최대 10,000건, 유저별 500건)

## 나중에
- [ ] 창 크기/위치 저장 및 복원
- [ ] 시스템 트레이 (최소화)
- [ ] 자동 업데이트 (tauri-plugin-updater + GitHub Releases)
- [ ] GitHub Actions CI/CD (.deb, .exe 자동 빌드)
- [ ] 다크/라이트 테마 전환
- [ ] 여러 스트리머 동시 모니터링 (탭)
