# ChzzkChat - 치지직 채팅 뷰어

치지직(Chzzk) 스트리밍 플랫폼의 실시간 채팅을 수집하고 표시하는 로컬 전용 GUI 애플리케이션.
**현재 Python Flet(Flutter) 기반으로 마이그레이션 진행중.** PyQt6 원본은 `pyqt6_legacy/`에 보관.

## 프로젝트 구조

```
ChzzkChat/
├── pyproject.toml       # Flet 프로젝트 설정
├── cookies.json         # 네이버 인증 쿠키 (gitignore)
├── settings.json        # 사용자 설정
├── .env                 # BUG_REPORT_EMAIL 설정
├── src/                 # Flet 앱 소스
│   ├── main.py          # Flet 앱 진입점
│   ├── config.py        # 경로/상수 설정 (재사용)
│   ├── api.py           # Chzzk API 호출 (재사용)
│   ├── cmd_type.py      # WS 명령어 타입 (재사용)
│   ├── chat_worker.py   # WebSocket 채팅 수신 (threading.Thread)
│   ├── chat_view.py     # 메인 채팅 UI
│   ├── chat_logger.py   # 채팅 로그 기록
│   └── dialogs.py       # Flet 다이얼로그
├── pyqt6_legacy/        # PyQt6 원본 보관
│   ├── main.py, api.py, cmd_type.py, run.py
│   └── src/ (main_window.py, workers.py, widgets.py, dialogs.py)
├── flet_app/            # Flet 프로토타입 (참조용)
├── img/                 # 앱 아이콘
├── cache/               # 배지/이모지 캐시
└── log/                 # 채팅 로그
```

## 데이터 구조

### chat_data (ChatWorker → 콜백)
```python
{
    'time': '15:30:00',
    'type': '채팅' | '후원',
    'uid': 'user_hash_id',
    'nickname': '닉네임',
    'message': '채팅 내용',
    'colorCode': 'CC000' | 'SG001~SG009',
    'badges': ['https://...'],
    'emojis': {'name': 'url'},
    'subscription_month': 29,
    'subscription_tier': 1,
    'os_type': 'PC' | 'MOBILE',
    'user_role': 'common_user' | 'manager' | 'streamer'
}
```

## 개발 환경
- Python 3.12
    - local venv 에서 작업할것
- Flet >= 0.80.5
- requests, websockets >= 16.0
- 실행: `flet run` (src/ 디렉토리)
