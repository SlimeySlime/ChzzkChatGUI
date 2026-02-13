# ChzzkChat Flet 마이그레이션 체크리스트

백지에서 재시작. 기능 1~2개씩 구현 + 테스트 반복.

## Step 1: 설정 + 쿠키 로딩
- [x] `src/config.py` — 경로 상수, .env 파싱
- [x] `src/main.py` — cookies.json 로드, 에러 시 스낵바
- [x] 테스트: 쿠키 있을 때/없을 때 동작 확인

## Step 2: API 레이어 + URL 파싱
- [x] `src/api.py` — fetch_chatChannelId, fetch_channelName, fetch_accessToken
- [x] `src/cmd_type.py` — CHZZK_CHAT_CMD 상수
- [ ] URL 입력 → 32자 hex 추출
- [ ] 연결 버튼 → API 호출 → 상태 갱신
- [ ] 테스트: 실제 UID → "연결 준비 완료" 확인

## Step 3: WebSocket ChatWorker
- [ ] `src/chat_worker.py` — threading.Thread 기반
- [ ] 연결/해제 토글
- [ ] 테스트: 실제 방송 연결 → 터미널에 메시지 print

## Step 4: 기본 채팅 표시
- [ ] chat_data → ft.Text Row → ListView
- [ ] auto_scroll 확인
- [ ] 테스트: 실시간 채팅 표시

## Step 5: 닉네임 색상 + 후원 구분
- [ ] COLOR_CODE_MAP + USER_COLOR_PALETTE
- [ ] 후원 메시지 배경색/prefix
- [ ] 테스트: 색상, 후원 구분 확인

## Step 6: 채팅 로깅
- [ ] `src/chat_logger.py`
- [ ] 날짜별 파일, 롤오버
- [ ] 테스트: 로그 파일 생성/내용 확인

## Step 7: 배지 + 이모지
- [ ] 배지 MD5 캐시 → ft.Image
- [ ] 이모지 {:name:} → ft.Image
- [ ] 테스트: 구독 배지, 이모지 렌더링

## Step 8: 메모리 관리 + 후원 필터
- [ ] 1만건 제한, 유저당 500건
- [ ] 후원 전용 보기 토글
- [ ] 채팅 초기화
- [ ] 테스트: 메모리, 필터 동작

## Step 9: 검색 + 닉네임 클릭 + 다이얼로그
- [ ] Ctrl+F 검색 바
- [ ] 닉네임 클릭 → UserChatDialog
- [ ] 설정/버그 리포트 다이얼로그
- [ ] 테스트: 검색, 팝업, 설정 적용

## Step 10: 마무리 + 빌드
- [ ] 종료 처리 (워커 정리, 설정 저장)
- [ ] flet build 테스트
- [ ] 통합 테스트

## 의도적 제외
- 시스템 트레이 (Flet 미지원)
- 최신채팅 오버레이 (나중에 ft.Stack)
- PyInstaller → `flet build` 사용

## 나중에
- [ ] 성능 테스트 — MAX_DISPLAY_MESSAGES / MAX_USER_MESSAGES 임계값 검증
- [ ] 자동 업데이트 — GitHub Releases 버전 체크 + 알림
- [ ] 이모지 GIF 애니메이션
- [ ] 다크/라이트 테마 전환
- [ ] 여러 스트리머 동시 모니터링 (탭)
- [ ] 빌드 자동화 스크립트
