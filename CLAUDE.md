# ChzzkChat - 치지직 채팅 뷰어

치지직(Chzzk) 스트리밍 플랫폼의 실시간 채팅을 수집하고 표시하는 PyQt6 기반 GUI 애플리케이션

## 프로젝트 구조

```
ChzzkChat/
├── main.py              # 앱 진입점 (QApplication 생성, 쿠키 로드)
├── api.py               # 치지직 API 호출 (채널ID, 토큰, 유저해시)
├── run.py               # CLI 실행 스크립트 (WebSocket 직접 연결)
├── cmd_type.py          # 치지직 채팅 WebSocket 명령어 타입
├── cookies.json         # 네이버 인증 쿠키 (gitignore)
├── settings.json        # 사용자 설정 (폰트, 창 크기)
├── img/
│   └── chzzk.png        # 앱 아이콘
├── src/
│   ├── config.py        # 경로 설정, 상수 (PyInstaller 호환)
│   ├── main_window.py   # 메인 UI 윈도우 (ChzzkChatUI)
│   ├── workers.py       # WebSocket 채팅 수신 워커 (ChatWorker)
│   ├── widgets.py       # 커스텀 위젯 (ClickableTextEdit)
│   └── dialogs.py       # 다이얼로그 (SettingsDialog, UserChatDialog)
├── cache/
│   ├── badges/          # 배지 이미지 캐시
│   └── emojis/          # 이모지 이미지 캐시
├── log/                 # 채팅 로그 (채널별/날짜별)
└── venv/
```

## 주요 클래스

| 클래스 | 파일 | 설명 |
|--------|------|------|
| `ChzzkChatUI` | `src/main_window.py` | 메인 윈도우 (연결, 채팅 표시, 로깅, 배치 전송) |
| `ChatWorker` | `src/workers.py` | QThread 기반 WebSocket 채팅 수신 |
| `ClickableTextEdit` | `src/widgets.py` | 닉네임 클릭 가능한 채팅 영역 |
| `SettingsDialog` | `src/dialogs.py` | 폰트 크기 등 설정 |
| `UserChatDialog` | `src/dialogs.py` | 유저 클릭 시 채팅 기록 팝업 |

## 구현된 기능

### UI
- 스트리머 UID/URL 입력 및 연결/해제 토글
- 메뉴바 (옵션/설정/트레이로)
- 시스템 트레이 아이콘
- 창 크기 저장/복원

### 채팅 표시
- 유저별 닉네임 색상 (colorCode 기반 + CC000 유저는 uid 해시 팔레트)
- 배지 표시 (구독/활동 배지, `cache/badges/`에 캐시)
- 이모지 표시 (`{:emojiName:}` → 이미지, `cache/emojis/`에 캐시)
- 닉네임 클릭 시 해당 유저 채팅 기록 팝업
- 스크롤 시 최신 채팅 오버레이

### URL 파싱 (`extract_streamer_id()`)
- `chzzk.naver.com/live/{uid}` 형태 URL에서 uid 추출
- uid 직접 입력도 지원

### 로깅
- Python logging + FileHandler
- 저장 경로: `log/{channel_name}/YYYY-MM-DD.log` (날짜별)
- 자정에 자동으로 새 파일 생성

### 설정
- `settings.json` - 폰트 크기 (8~24pt), 창 크기 저장
- PyInstaller 빌드 시 경로 자동 처리 (`config.py`)

### 서버 배치 전송 (롤백 예정)
- `config.py`: `API_SERVER_URL`, `API_KEY` 하드코딩
- `main_window.py`: 1분마다 `POST /chat/bulk` 배치 전송
- 1000건 초과시 즉시 전송
- **TODO에서 롤백 예정** — 일반 사용자용 로컬 채팅 로그 뷰어로 전환

## 데이터 구조

### chat_data (ChatWorker → ChzzkChatUI 시그널)
```python
{
    'time': '15:30:00',           # 시:분:초
    'type': '채팅' | '후원',
    'uid': 'user_hash_id',
    'nickname': '닉네임',
    'message': '채팅 내용',
    'colorCode': 'CC000' | 'SG001~SG009',
    'badges': ['https://...'],    # 배지 이미지 URL 리스트
    'emojis': {'name': 'url'},    # 이모지 이름→URL 매핑
    'subscription_month': 29,     # 구독 개월 (None 가능)
    'subscription_tier': 1,       # 구독 티어 (None 가능)
    'os_type': 'PC' | 'MOBILE',   # (None 가능)
    'user_role': 'common_user' | 'manager' | 'streamer'  # (None 가능)
}
```

## 개발 환경
- Python 3.12
- PyQt6 >= 6.6.0
- websocket-client
- requests