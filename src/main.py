"""ChzzkChat - Flet 앱 진입점"""

import json
import os

import flet as ft

from config import COOKIES_PATH


def main(page: ft.Page):
    # ── 윈도우 설정 ──
    page.title = "Chzzk Chat"
    page.window.width = 500
    page.window.height = 600
    page.window.min_width = 350
    page.window.min_height = 400
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # ── 쿠키 로드 ──
    cookies = {}
    if os.path.exists(COOKIES_PATH):
        try:
            with open(COOKIES_PATH, encoding='utf-8') as f:
                cookies = json.load(f)
        except Exception as e:
            page.open(ft.SnackBar(
                content=ft.Text(f"cookies.json 파싱 실패: {e}"),
                bgcolor=ft.Colors.RED_900,
            ))
    else:
        page.open(ft.SnackBar(
            content=ft.Text("cookies.json 파일이 없습니다. 네이버 인증 쿠키를 설정해주세요."),
            bgcolor=ft.Colors.RED_900,
        ))

    # ── 상단: URL 입력 영역 ──
    url_input = ft.TextField(
        label="스트리머 UID",
        hint_text="UID 또는 URL 입력",
        expand=True,
        height=48,
        border_color=ft.Colors.GREY_700,
        focused_border_color=ft.Colors.GREEN,
        text_size=14,
    )

    connect_btn = ft.Button(
        content=ft.Text("연결", weight=ft.FontWeight.BOLD),
        color=ft.Colors.BLACK,
        bgcolor=ft.Colors.GREEN,
        height=48,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=4),
        ),
    )

    connect_row = ft.Row(
        controls=[url_input, connect_btn],
        spacing=8,
    )

    # ── 상태 표시 ──
    status_text = ft.Text(
        value="스트리머 주소를 입력하고 연결 버튼을 눌러주세요",
        size=12,
        color=ft.Colors.GREY_500,
    )

    # ── 채팅 표시 영역 ──
    chat_list = ft.ListView(
        expand=True,
        spacing=2,
        auto_scroll=True,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
    )

    chat_container = ft.Container(
        content=chat_list,
        expand=True,
        border=ft.Border.all(1, ft.Colors.GREY_800),
        border_radius=4,
        bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
    )

    # ── 메뉴바 ──
    menubar = ft.MenuBar(
        controls=[
            ft.SubmenuButton(
                content=ft.Text("옵션", size=13),
                controls=[
                    ft.MenuItemButton(
                        content=ft.Text("후원만 보기"),
                        leading=ft.Icon(ft.Icons.VOLUNTEER_ACTIVISM, size=18),
                    ),
                    ft.MenuItemButton(
                        content=ft.Text("채팅 내역 초기화"),
                        leading=ft.Icon(ft.Icons.DELETE_SWEEP, size=18),
                    ),
                    ft.Divider(height=1),
                    ft.MenuItemButton(
                        content=ft.Text("종료"),
                        leading=ft.Icon(ft.Icons.EXIT_TO_APP, size=18),
                    ),
                ],
            ),
            ft.SubmenuButton(
                content=ft.Text("설정", size=13),
                controls=[
                    ft.MenuItemButton(
                        content=ft.Text("설정 열기"),
                        leading=ft.Icon(ft.Icons.SETTINGS, size=18),
                    ),
                ],
            ),
            ft.SubmenuButton(
                content=ft.Text("도움말", size=13),
                controls=[
                    ft.MenuItemButton(
                        content=ft.Text("버그 리포트"),
                        leading=ft.Icon(ft.Icons.BUG_REPORT, size=18),
                    ),
                ],
            ),
        ],
        style=ft.MenuStyle(
            bgcolor=ft.Colors.GREY_900,
        ),
    )

    # ── 페이지 레이아웃 조립 ──
    page.add(
        ft.Column(
            controls=[
                menubar,
                ft.Container(
                    content=ft.Column(
                        controls=[
                            connect_row,
                            status_text,
                            chat_container,
                        ],
                        spacing=8,
                        expand=True,
                    ),
                    padding=ft.Padding.all(12),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        ),
    )


ft.run(main)
