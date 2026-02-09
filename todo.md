# ChzzkChat TODO
# 한 항목당 최대 두줄로 정리합니다.
# 수정 내역은 Changelog 항목에, 완전히 반영된 내역은 CLAUDE.md 에 정리합니다.

## Flet 마이그레이션 (진행중)

PyQt6 → Python Flet(Flutter) 전환. PyQt6 원본은 `pyqt6_legacy/` 에 보관.

### Phase 1: 프로젝트 구조 + ChatWorker ✅
- [x] pyproject.toml 의존성 추가 (requests, websockets)
- [x] api.py, cmd_type.py → src/ 복사
- [x] PyQt6 파일 → pyqt6_legacy/ 이동
- [x] src/chat_worker.py — QThread→threading.Thread, pyqtSignal→콜백, websockets.sync

### Phase 2: 코어 채팅 UI ✅
- [x] src/main.py — Flet 앱 진입점 (cookies.json 로드)
- [x] src/chat_view.py — URL 입력, 연결/해제, ListView 채팅, AppBar 메뉴
- [x] 닉네임 색상 (COLOR_CODE_MAP + USER_COLOR_PALETTE)
- [x] 후원 메시지 배경색 구분

### Phase 3: 배지 + 이모지 + 닉네임 클릭 ✅
- [x] 배지: ft.Image(src=url) 닉네임 앞
- [x] 이모지: {:name:} → Text/Image 분할
- [x] 닉네임 클릭 → UserChatDialog (AlertDialog)

### Phase 4: 검색 + 후원 전용 모드 ✅
- [x] Ctrl+F 검색 바, 하이라이트, 이전/다음
- [x] 후원 전용 필터 토글

### Phase 5: 로깅 + 메모리 관리 + 설정 ✅
- [x] src/chat_logger.py — 로그 파일 기록
- [x] 메모리 제한 (표시 1만건, 유저당 500건)
- [x] 설정 다이얼로그 (폰트 크기)
- [x] 버그 리포트 (mailto:)

### 의도적 제외
- 시스템 트레이 (Flet 미지원)
- 최신채팅 오버레이 (나중에 ft.Stack)
- 창 크기 저장/복원 (Flet 자체 관리)
- PyInstaller → `flet build` 사용

## 마이그레이션 이후 버그
- log 기록에서 logger를 처음 지정해줄때 생기는, == 채팅 수집 시간
메시지가 로깅시에 매번 기록되고있음
(e.g) 
=== 채팅 수집 시작: 2026-02-09 15:18:38 ===
[15:18:37][채팅][bdf6c0a9a0e72ff77440c7d728a5ea88] ㅇELIㅇ: 어어~~~~~어~

=== 채팅 수집 시작: 2026-02-09 15:18:40 ===
[15:18:40][채팅][7fc9dac73043f7f6281eac0357925ee3] 우리집금붕어fXukumfXukum: 와..
[15:18:40][채팅][0494eb4493e889c919ca36cced24cccf] 탄산음료: 못참고 홈런을 그만ㅋㅋㅋㅋㅋㅋ


## 나중에

- [ ] 성능 테스트 — MAX_DISPLAY_MESSAGES / MAX_USER_MESSAGES 임계값 검증
- [ ] 자동 업데이트 — GitHub Releases 버전 체크 + 알림
- [ ] 이모지 GIF 애니메이션
- [ ] 다크/라이트 테마 전환
- [ ] 여러 스트리머 동시 모니터링 (탭)
- [ ] 빌드 자동화 스크립트

---

## 완료

- [x] 버그리포트 기능 — 메뉴바 추가, .env 메일 설정, mailto: 전송 (2026-02-09)
- [x] 채팅 검색 (Ctrl+F) — 검색 바 토글, 하이라이트, 이전/다음 이동 (2026-02-09)
- [x] 후원 전용 보기 모드 — 토글로 후원 채팅만 필터링, all_messages 재렌더링 (2026-02-09)
- [x] 서버 연동 롤백 — API 인증/key/서버 전송 코드 제거 (2026-02-09)
- [x] 채팅 메모리 관리 — 표시 1만건, 유저당 500건 제한 (2026-02-09)
- [x] URL 파싱 확장 — 32자 hex 추출, chzzk.naver.com/live 버그 수정 (2026-02-09)
- [x] bare except 로깅 — debug/warning 레벨로 에러 기록 (2026-02-09)
- [x] 채팅 수동 클리어 — 옵션 메뉴 '채팅 내역 초기화' (2026-02-09)
- [x] 코드 모듈화 — main.py + src/ 구조 (2025-01-30)
- [x] PyInstaller 빌드 (2025-01-30)
- [x] 설정 메뉴 (폰트 크기)
- [x] 이모지 표시 (정적 이미지)
- [x] 로그 파일명: `log/{channel_name}/YYYY-MM-DD.log`
- [x] 창 크기 저장/복원
