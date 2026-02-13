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
