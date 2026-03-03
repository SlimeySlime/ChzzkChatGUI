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

## Phase 5: 채팅 기능 완성 ✅
- [x] 닉네임 색상 (color_code 기반, 해시 팔레트) — Phase 2에서 완료
- [x] 배지 이미지 렌더링 (최대 3개) — Phase 2에서 완료
- [x] 후원 메시지 강조 표시 (배경색) — Phase 2에서 완료
- [x] 후원만 보기 토글 — Phase 2에서 완료
- [x] 설정 (타임스탬프, 배지 표시 토글) — Phase 2에서 완료
- [x] 메모리 관리 (최대 50,000건) — Phase 4에서 완료, Phase 8 이후 상향
- [x] 채팅 로그 파일 기록 (log/{channel}/YYYY-MM-DD.log)
- [x] 설정 확장 (폰트 크기 UI, 설정 영구 저장)

## Phase 6: 편의 기능 ✅
- [x] 이모지 치환 + 이미지 캐시
  - [x] `types.rs`: ChatData에 `emojis: HashMap<String, String>` 필드 추가
  - [x] `chat.rs`: extras에서 emojis 파싱 후 ChatData에 포함
  - [x] `ChatItem.tsx`: `{:name:}` 패턴을 `<img>` 태그로 렌더링
  - [x] 배지/이모지 URL → 로컬 파일 캐시 (재시작 후 재사용)
- [x] 검색 기능 (Ctrl+F, 닉네임/메시지 필터)
- [x] 유저별 채팅 이력 (닉네임 클릭 → 해당 유저 채팅만 표시)
- [x] 메모리 관리 고도화 (유저별 최근 500건 제한)

## Phase 7: 앱 완성도 개선 ✅
- [x] 앱 아이콘 적용 (chzzk.png → Tauri 아이콘 생성 + MenuBar 표시)
- [x] 이미지 캐시 채널별 분리 (`cache/{channel_name}/`)
- [x] 창 크기/위치 저장 및 복원 (tauri-plugin-window-state)
- [x] 시스템 트레이 (닫기 → 트레이 최소화, 클릭 → 창 표시/숨기기 토글)

## 버그발견
- [x] 트레이아이콘 버튼 아무런 동작안함
- [x] 채팅이 빠르게 올라오는 경우, 스크롤이 아래에 있어도 새 채팅이 올라와도 최신 채팅으로 포커싱이 안되고, 스크롤이 고정되어있는 경우가 생김
- [x] 메뉴바 버튼 클릭시 드롭다운이 열리고, 다시 클릭시에 드롭다운이 해제되지않음
- [x] dev 구동시와는 달리, build된 .exe파일 구동시 log 폴더 없음

## Phase 8: 가상 스크롤 ✅
- [x] `@tanstack/react-virtual` 설치
- [x] `ChatList.tsx`: `useVirtualizer` 적용 — 화면에 보이는 항목만 DOM에 렌더링
- [x] `ChatItem.tsx`: `React.memo` 적용 — 불필요한 재렌더링 방지
- [x] 자동 스크롤 유지 — `virtualizer.scrollToIndex` + `isProgrammaticRef` 연동

## Phase 9: 버그 수정 ✅
- [x] 메뉴바 드롭다운 재클릭 시 안 닫히는 버그 수정 (CSS → React state)
- [x] 빌드 `.exe` 실행 시 log 폴더 잘못된 경로 버그 수정 (`cfg!(debug_assertions)` 분기)
- [x] 창 크기·위치를 `tauri-plugin-window-state` 대신 `settings.json`으로 통합 관리

## Phase 10: 다크/라이트 테마 전환
- [ ] Tailwind `dark:` prefix + `<html class="dark">` 토글
- [ ] `Settings`에 `theme` 필드 추가 및 복원
- [ ] MenuBar 설정 드롭다운에 전환 버튼 추가

## Phase 11: 여러 스트리머 동시 모니터링 (탭)
- [ ] Rust: `ChatState` → `HashMap<uid, AbortHandle>`, 이벤트명 `chat-message-{uid}` 분리
- [ ] Frontend: `tabs[]` state, `activeTab`, 탭바 UI
- [ ] 탭 최대 수 제한 (예: 5개), 전역 설정 공유

## 나중에 (배포, 최후순위)
- [ ] 자동 업데이트 (tauri-plugin-updater + GitHub Releases)
- [ ] GitHub Actions CI/CD (.deb, .exe 자동 빌드)
