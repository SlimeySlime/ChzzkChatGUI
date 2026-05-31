# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.6.0] - 2026-05-27

### 추가
- 앱 내 쿠키 설정 UI 추가 — 설정 메뉴 → "쿠키 설정"에서 NID_AUT / NID_SES를 직접 입력하고 저장 가능
- 도움말 메뉴에 현재 앱 버전 표시 추가

### 수정
- 메뉴바 Chzzk 아이콘이 표시되지 않던 문제 수정 (잘못된 파일명 참조)

---

## [0.5.0] - 2026-03-13

### 변경
- Tauri 앱 서명 키 적용 — 자동 업데이트 서명 검증 활성화

---

## [0.4.0] - 2026-03-13

### 변경
- 서명 키 교체 및 버전 업

---

## [0.3.0] - 2026-03-11

### 제거
- 개발용 테스트 코드 정리

---

## [0.2.0] - 2026-03-11

### 추가
- 멀티탭 지원 — 최대 5개 스트리머 동시 모니터링
- 라이트 / 다크 테마 토글 (설정 메뉴)
- 창 크기·위치 저장 및 재시작 시 복원
- 자동 업데이트 지원 (GitHub Releases 기반)
- GitHub Actions 릴리즈 자동 빌드 워크플로우
- 트레이 아이콘 지원 — 최소화 후 트레이에서 복원 가능
- 메뉴 드롭다운 UI (옵션 / 설정)
- Ctrl+F 채팅 검색 기능

### 수정
- 가상 스크롤 렌더링 오류 수정 및 메모리 누수 개선

---

## [0.1.0] - 2026-03-12

### 추가
- Tauri (React + TypeScript + Rust) 기반 초기 구현
- Chzzk WebSocket 채팅 연결 및 실시간 수신
- 배지·이모지 로컬 캐시 다운로드
- 설정 저장/로드 (settings.json)
- 채팅 로그 파일 기록 (log/)
- 후원 메시지 강조 표시
- 시스템 트레이 아이콘

[0.6.0]: https://github.com/SlimeySlime/ChzzkChatGUI/releases/tag/v0.6.0
[0.5.0]: https://github.com/SlimeySlime/ChzzkChatGUI/releases/tag/v0.5.0
[0.4.0]: https://github.com/SlimeySlime/ChzzkChatGUI/releases/tag/v0.4.0
[0.3.0]: https://github.com/SlimeySlime/ChzzkChatGUI/releases/tag/v0.3.0
[0.2.0]: https://github.com/SlimeySlime/ChzzkChatGUI/releases/tag/v0.2.0
[0.1.0]: https://github.com/SlimeySlime/ChzzkChatGUI/releases/tag/v0.1.0
