# ChzzkChat Flet 마이그레이션 진행 기록

각 단계 구현 후 테스트 결과를 기록합니다.

---

## Step 1: 설정 + 쿠키 로딩 ✅

### 구현 내용

**`src/config.py`**
- 경로 상수 7개: `BASE_DIR`, `CACHE_DIR`, `BADGE_CACHE_DIR`, `EMOJI_CACHE_DIR`, `LOG_DIR`, `SETTINGS_PATH`, `COOKIES_PATH`, `ENV_PATH`
- `.env` 파서: `KEY=VALUE` 형식, 주석(`#`) 무시, 따옴표 제거
- `BUG_REPORT_EMAIL` 환경변수 로드
- 디렉토리 자동 생성: `cache/badges/`, `cache/emojis/`, `log/`

**`src/main.py`**
- `cookies.json` 로드: 파일 존재 시 JSON 파싱, 실패 시 빨간 스낵바 표시
- 쿠키 파일 없을 때: "cookies.json 파일이 없습니다" 스낵바 표시
- UI 스켈레톤 구성 (Step 1 범위 초과, 미리 구성):
  - 메뉴바: 옵션(후원만 보기, 채팅 초기화, 종료), 설정, 도움말(버그 리포트)
  - URL 입력 필드 + 연결 버튼 (on_click 미연결)
  - 상태 텍스트
  - 채팅 ListView (auto_scroll=True)

### 비고
- `src/api.py`, `src/cmd_type.py`는 레거시에서 재사용하여 이미 구현 완료 (Step 2 범위)
- 연결 버튼 이벤트, URL 파싱은 Step 2에서 연결 예정

---

## Step 2: API 레이어 + URL 파싱 ✅

### 구현 내용

**`src/main.py` — URL 파싱 + 연결 이벤트**
- `extract_streamer_id()` 함수 추가: `re.search(r'[a-f0-9]{32}')` 패턴으로 32자 hex UID 추출
- `on_connect_clicked()` 콜백: 연결 버튼 클릭 시 API 호출
  - `api.fetch_channelName(uid)` → 채널명 가져오기
  - `api.fetch_chatChannelId(uid, cookies)` → chatChannelId 획득
  - 성공: status_text에 "{채널명} 연결 준비 완료" 표시 (초록)
  - 실패: status_text에 에러 메시지 표시 (빨강)
  - API 호출 중 버튼 비활성화 + threading으로 UI 블록 방지

**`tests/test_step2.py` — pytest 테스트 (신규)**
- URL 파싱 테스트 7개: 직접 UID, /live/ URL, 채널 URL, chzzkban URL, 공백, 잘못된 입력, 빈 문자열
- API 호출 테스트 1개: `fetch_channelName` (공개 API)
- 결과: 8/8 통과

### Flet API 주의사항
- `page.open()` → Flet 0.80에서 제거됨, `page.show_dialog()` 사용
- `ft.Button` → `on_click` 파라미터로 콜백 연결

---

## Step 3: WebSocket ChatWorker ✅ (코드 + 단위 테스트)

### 구현 내용

**`src/chat_worker.py` (신규)**
- `ChatWorker(threading.Thread)` — daemon 스레드
- `connect_chat()`: API 4종 호출 → WS 연결 → CMD 100 인증 → CMD 5101 최근채팅
- `run()`: 메인 루프 — ping/pong, 채팅/후원 메시지 수신, 자동 재연결
- `_process_chat_data()`: profile/extras JSON 파싱 → chat_data dict 구성
- `stop()`: running=False + sock.close()
- PyQt6 시그널 → 콜백 함수(on_chat, on_status)로 변환

**`src/main.py` 수정**
- `on_connect_clicked()`: ChatWorker 시작/중지 토글
- `on_chat_received()`: 터미널 print (Step 4에서 UI 연결 예정)
- `on_status_changed()`: status_text 갱신 + 버튼 상태 변경
- 연결 시 버튼 "해제"(빨강) / 해제 시 "연결"(초록) 전환

**`tests/test_step3.py` (신규) — 10개 테스트**
- 기본 채팅, 익명 후원자, 색상 코드, 구독 배지, 활동 배지
- 이모지/OS타입, 시간 형식, msg 없는 데이터 스킵, 프로필 파싱 실패 스킵
- ChatWorker 생성/중지 라이프사이클

### 의존성 추가
- `websocket-client` 패키지 설치 필요 (pyproject.toml의 `websockets`와 별개)

### 남은 작업
- `flet run`으로 실제 방송 연결 테스트 (cookies.json + 라이브 방송 필요)

---

## Step 4: 기본 채팅 표시 + 닉네임 색상 ✅

### 구현 내용

**`src/main.py` — 채팅 UI 렌더링**
- `COLOR_CODE_MAP`: 프리미엄 닉네임 색상 9종 (SG001~SG009)
- `USER_COLOR_PALETTE`: 일반 유저 12색 팔레트 (`hash(uid)` 기반 고정 할당)
- `get_user_color()`: 프리미엄 코드 우선, 없으면 해시 팔레트
- `on_chat_received()`: chat_data → ft.Row(시간 + 닉네임 + 메시지) → ListView
  - 후원: 금색(`#ffcc00`) 닉네임 + `[후원]` prefix + 반투명 금색 배경
  - 일반: 해시 기반 닉네임 색상 + 흰색 메시지

### 비고
- Step 5(닉네임 색상 + 후원 구분)를 Step 4에 통합

---

## asyncio 전환 (핫픽스) ✅

### 문제
- `threading.Thread`(ChatWorker)에서 `page.update()` 호출 시 UI 미갱신
- 윈도우 포커스 이동 후에만 채팅이 표시되는 현상
- `threading.Lock` 적용해도 해결 안 됨 (index out of range 에러 발생)
- Flet GitHub Issue #3571, #5902 — threading 앱은 `flet build`에서도 프리즈

### 원인
Flet은 async-first 프레임워크. 백그라운드 스레드에서 page.update()를 호출하면
내부 상태와 UI 렌더링이 동기화되지 않음.

### 해결
`chat_worker.py`와 `main.py`를 async 패턴으로 전환:

1. **`chat_worker.py` 전체 재작성**
   - `threading.Thread` → 일반 클래스 + `async def run()`
   - `websocket-client` (동기) → `websockets` (비동기, pyproject.toml에 이미 있음)
   - `api.fetch_*()` (동기 requests) → `asyncio.to_thread()`로 감싸서 이벤트 루프 블록 방지
   - `stop()` → `async def stop()` + `await self.ws.close()`

2. **`main.py` async 전환**
   - `def main(page)` → `async def main(page)`
   - `worker.start()` → `page.run_task(worker.run)` (Flet 이벤트 루프에서 실행)
   - `worker.is_alive()` → `worker.running` (Thread가 아니므로)
   - `on_connect_clicked` → `async def` + `await worker.stop()`
   - 연결 완료 시 `connect_btn.disabled = False` 추가 (해제 버튼 버그 동시 수정)

### 핵심 원리
```
page.run_task(worker.run)
  → worker.run()이 Flet 이벤트 루프에서 실행됨
  → 콜백(on_chat, on_status)도 같은 루프에서 호출
  → page.update()가 즉시 UI에 반영 (스레드 경합 없음)
```

### 의존성 변경
- `websocket-client` 더 이상 불필요 (동기 WebSocket 라이브러리)
- `websockets>=16.0` 사용 (비동기, pyproject.toml에 기존 포함)
