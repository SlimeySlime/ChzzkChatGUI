"""
ChzzkChat 메인 진입점
"""
import sys
import json
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from src.config import COOKIES_PATH, ICON_PATH
from src.main_window import ChzzkChatUI


def main():
    # 쿠키 파일 확인
    if not os.path.exists(COOKIES_PATH):
        print(f"오류: {COOKIES_PATH} 파일이 없습니다.")
        print("Naver 인증 쿠키(NID_AUT, NID_SES)를 cookies.json에 저장해주세요.")
        sys.exit(1)

    with open(COOKIES_PATH) as f:
        cookies = json.load(f)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 앱 전체 아이콘 설정
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = ChzzkChatUI(cookies)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
