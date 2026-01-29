# TODO

## 우선순위 높음

- [x] 로그 파일명 변경: `chat.log` → `{YYYY-MM-DD}.log` 형태로 변경
  - ~~현재: `log/{channel_name}/chat.log` + 로테이션 시 `.YYYY-MM-DD.log` suffix~~
  - 변경 완료: `log/{channel_name}/YYYY-MM-DD.log` 직접 생성

- [ ] 배포판 테스트하기
  > pyinstaller 또는 Nuitka 중에 결정 (뭐가 더 좋을까?)
  > pyinstaller --onedir 방법 생각중
- [ ] 자동 업데이트 방법 고안 
  > (실행 시에 version 정보를 서버와 확인해서, 자동업데이트되게끔 )

## 기능 개선

- [x] 설정 메뉴 구현
  - 폰트 크기 조절 (8~24pt)
  - settings.json에 저장/로드
- [x] 이모지 표시 지원 (extras.emojis 파싱)
  - {:emojiName:} 형태를 이미지로 치환
  - cache/emojis/ 에 이미지 캐시
  -[ ] 이모지 gif 표시 지원
    (현재는 gif 이모지가 gif로 출력이 안되고 정지 png로 나온다)

## UI 개선

- [ ] 채팅창 폰트 크기 조절 옵션
- [ ] 다크/라이트 테마 전환
  (엄청 여러줄의 stylesheet 코드 대신, 다른 방법이 존재할까?)
- [ ] 창 크기 및 위치 저장/복원
  (지금은 UserChatDialog가 특정 좌표에 고정되어서 팝업되는데, 이게 현재 MainWindow 위치 기준으로 팝업되게 바꾸고싶어)

## 기타
(기타는 좀 나중에 해도 돼)
- [ ] 에러 핸들링 개선 (연결 실패 시 재시도 옵션)
- [ ] 여러 스트리머 동시 모니터링 (탭 형태)
