"""
ChzzkChat Flet 앱 진입점
"""
import json
import os

import flet as ft

from config import COOKIES_PATH
from chat_view import ChzzkChatApp


def main(page: ft.Page):
    # 쿠키 로드
    if not os.path.exists(COOKIES_PATH):
        page.add(ft.Text(
            f"오류: {COOKIES_PATH} 파일이 없습니다.\n"
            "Naver 인증 쿠키(NID_AUT, NID_SES)를 cookies.json에 저장해주세요.",
            color=ft.Colors.RED_400, size=14,
        ))
        return

    with open(COOKIES_PATH) as f:
        cookies = json.load(f)

    app = ChzzkChatApp(page, cookies)
    app.build()


ft.run(main)
