# ChzzkChatGUI 프로젝트 요약

## 프로젝트 개요
치지직(Chzzk) 스트리밍 플랫폼의 실시간 채팅을 수집하고 표시하는 PyQt6 기반 GUI 애플리케이션

## 핵심 구조

### 파일 구성
- `ui.py` - 메인 GUI 애플리케이션 (PyQt6)
- `api.py` - 치지직 API 연동
- `run.py` - CLI 실행 스크립트
- `cmd_type.py` - 치지직 채팅 명령어 타입 정의
- `cookies.json` - 인증 쿠키 (gitignore)

### 주요 클래스
- `ChatWorker(QThread)` - WebSocket 채팅 수신 워커
- `ChzzkChatUI(QMainWindow)` - 메인 윈도우
- `ClickableTextEdit(QTextEdit)` - 클릭 가능한 채팅 표시 영역
- `UserChatDialog(QDialog)` - 유저 채팅 기록 팝업
- `SettingsDialog(QDialog)` - 설정 다이얼로그

## 구현된 기능

### UI
- 스트리머 UID 입력 및 연결/해제 토글
- 메뉴바 (옵션/설정/트레이로)
- 시스템 트레이 아이콘
- 윈도우/트레이 아이콘 (img/chzzk.png)

### 채팅 표시
- 유저별 닉네임 색상 (colorCode 기반 + CC000 유저는 uid 해시 팔레트)
- 배지 표시 (구독/활동 배지, cache/badges/ 에 이미지 캐시)
- 이모지 표시 ({:emojiName:} → 이미지, cache/emojis/ 에 캐시)
- 닉네임 클릭 시 해당 유저 채팅 기록 팝업
- 스크롤 시 최신 채팅 오버레이

### 로깅
- Python logging + FileHandler
- 저장 경로: `log/{channel_name}/YYYY-MM-DD.log` (날짜별 파일)
- 자정에 자동으로 새 파일 생성

### 설정
- `settings.json` - 사용자 설정 저장
- 폰트 크기 조절 (8~24pt)

## 데이터 구조

### chat_data profile 필드
```json
{
  "nickname": "유저명",
  "streamingProperty": {
    "nicknameColor": { "colorCode": "CC000" },
    "subscription": {
      "accumulativeMonth": 29,
      "tier": 1,
      "badge": { "imageUrl": "..." }
    }
  },
  "activityBadges": [{ "imageUrl": "...", "activated": true }]
}
```

### colorCode
- `CC000` - 일반 유저 (uid 해시 기반 팔레트 색상)
- `SG001~SG009` - 치트키 사용자 (고정 색상)

## 서버 연동 (구현 완료)

### 배치 전송 기능
- `src/config.py`: `API_SERVER_URL`, `API_KEY` 설정
- `src/main_window.py`:
  - `chat_buffer`: 채팅 임시 저장 리스트
  - `batch_timer`: 1분마다 배치 전송 (QTimer)
  - `send_batch_to_server()`: `POST /chat/bulk`로 전송 (`Authorization: Bearer` 헤더 포함)
  - 1000건 초과시 즉시 전송

### 전송 데이터 구조
```json
{
  "channel_id": "스트리머 해시 ID",
  "channel_name": "스트리머명",
  "user_id": "시청자 해시 ID",
  "nickname": "닉네임",
  "message": "채팅 내용",
  "message_type": "chat/donation",
  "chat_time": "2026-02-04T12:00:00",
  "subscription_month": 29,
  "subscription_tier": 1,
  "os_type": "PC/MOBILE",
  "user_role": "common_user/manager/streamer"
}
```

### 관련 파일
- `src/workers.py`: ChatWorker에서 채팅 파싱 시 추가 데이터 추출
- `src/main_window.py`: 버퍼 관리 및 배치 전송

## 개발 환경
- Python 3.12
- PyQt6 >= 6.6.0
- requests (서버 통신)
- venv: `venv/`
