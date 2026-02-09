# TODO

## 현재 진행 예정 (우선순위)

https://chzzk.naver.com/live/a9a343510e132ea3026ff3cf682820b5
와 같은 url도 적절히 parsing해서 uid 부분만 추출한뒤 연결 가능해야함
(uid 직접 입력과, 주소전체 입력 모두 연결 가능하게끔)

### 1. 자동 업데이트 구현
- [ ] 버전 관리 시스템 구축
  - `version.py` 또는 `__version__` 상수 추가
  - GitHub Releases에 버전 태그
- [ ] 업데이트 체크 로직
  - 앱 시작 시 GitHub API로 최신 버전 확인
  - `https://api.github.com/repos/{owner}/{repo}/releases/latest`
- [ ] 업데이트 알림 UI
  - 새 버전 있으면 다이얼로그로 알림
  - "다운로드" 버튼 → 브라우저로 릴리즈 페이지 열기
  - (자동 다운로드+설치는 복잡하므로 나중에)

### 2. 이모지 GIF 애니메이션 지원
- [ ] 문제 분석
  - QTextEdit의 `<img>` 태그는 GIF 애니메이션 미지원 (Qt 한계)
  - 해결 방안:
    1. **QLabel + QMovie 오버레이** - 복잡함
    2. **QListWidget 기반 채팅창** - 각 메시지를 위젯으로
    3. **WebEngineView** - HTML 렌더링 (무거움)
    4. **GIF → 정지 이미지 유지** - 현실적 타협
  - 결정 필요: 노력 대비 효과 고려

### 3. 창 크기 저장 + ChatDialog 상대위치
- [ ] MainWindow 크기 저장
  - `closeEvent`에서 `self.size()` 저장
  - settings.json에 `window_width`, `window_height` 추가
  - 앱 시작 시 저장된 크기로 복원
- [ ] UserChatDialog 상대위치 팝업
  - 현재: 고정 좌표 `setGeometry(200, 200, ...)`
  - 변경: MainWindow 중앙 또는 우측에 팝업
  - `parent.geometry()` 기준으로 계산

---

## 중요: 채팅 로그 DB 저장

### 문제점
- 클라이언트 앱에 PostgreSQL 자격증명(IP/PW)을 직접 넣으면 **보안 위험**
- 빌드된 앱을 디컴파일하면 DB 정보 노출

### 해결 방안: API 서버 구축

```
[ChzzkChat 클라이언트]
        ↓ HTTP POST (채팅 데이터)
[API 서버 (FastAPI/Flask)]
        ↓ DB 연결
[PostgreSQL]
```
(구현 과정은 내가 지웠어. todo.md가 너무 지저분해져서)


### 클라이언트 설정 UI
- [ ] 설정 다이얼로그에 "클라우드 동기화" 섹션 추가
  - API 서버 URL 입력
  - API Key 입력
  - "연결 테스트" 버튼
  - ON/OFF 토글

---

## 완료된 항목

- [x] 로그 파일명 변경: `log/{channel_name}/YYYY-MM-DD.log`
- [x] 코드 모듈화 (2025-01-30)
- [x] PyInstaller 배포판 테스트 (2025-01-30)
- [x] 설정 메뉴 구현 (폰트 크기)
- [x] 이모지 표시 지원 (정적 이미지)
- [x] 채팅창 폰트 크기 조절

---

## UI 개선

- [ ] 다크/라이트 테마 전환
  - 현재: 하드코딩된 stylesheet
  - 개선안: QSS 파일 분리 또는 QPalette

---

## 배포 관련

- [ ] 빌드 자동화 스크립트 (`build.py`)
- [ ] Windows 빌드 테스트
<!-- onedir 방식 유지, 설치 패키지는 불필요 -->

---

## 코드 품질

- [ ] 기존 ui.py 정리/삭제 (새 구조와 중복)
- [ ] 타입 힌트 추가
- [ ] 에러 핸들링 개선

---

## 기타 (나중에)

- [ ] 여러 스트리머 동시 모니터링 (탭 형태)
- [ ] 채팅 필터링 (특정 유저, 키워드)
- [ ] 채팅 통계 (활성 유저 수, 메시지 수)
