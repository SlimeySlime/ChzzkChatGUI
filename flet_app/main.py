"""
ChzzkChat Flet 마이그레이션 테스트
- Getting Started: 기본 레이아웃 + 다크 테마 + 채팅 메시지 표시 테스트
"""
import datetime

import flet as ft


def main(page: ft.Page):
    # 기본 설정
    page.title = "ChzzkChat (Flet Test)"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 500
    page.window.height = 700
    page.padding = 0

    # 상태
    connected = False

    # ── 채팅 메시지 리스트 ──
    chat_list = ft.ListView(
        expand=True,
        spacing=2,
        auto_scroll=True,
    )

    # 상태 표시 라벨
    status_label = ft.Text(
        "연결 대기중",
        size=12,
        color=ft.Colors.GREY_500,
    )

    def add_chat_message(nickname, message, color="#00ff00", msg_type="채팅"):
        """채팅 메시지를 리스트에 추가"""
        time_str = datetime.datetime.now().strftime("%H:%M:%S")

        # 후원 메시지는 노란색 배경
        bg_color = "#3d3d00" if msg_type == "후원" else "#252525"

        msg_row = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"[{time_str}]", size=11, color=ft.Colors.GREY_500),
                    ft.Text(
                        nickname,
                        size=12,
                        color=color,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(message, size=12, color=ft.Colors.WHITE),
                ],
                spacing=8,
            ),
            bgcolor=bg_color,
            padding=ft.Padding.all(6),
            border_radius=3,
        )
        chat_list.controls.append(msg_row)
        page.update()

    def on_connect_click(e):
        nonlocal connected
        uid = url_input.value.strip()
        if not uid:
            status_label.value = "UID 또는 URL을 입력하세요"
            status_label.color = ft.Colors.RED_400
            page.update()
            return

        if not connected:
            # 연결 시뮬레이션
            connected = True
            connect_btn.content = "연결 해제"
            connect_btn.bgcolor = "#cc0000"
            status_label.value = f"연결됨: {uid[:16]}..."
            status_label.color = ft.Colors.GREEN_400
            url_input.disabled = True

            # 테스트 메시지 추가
            add_chat_message("시스템", "채팅에 연결되었습니다.", color="#888888")
            add_chat_message("테스트유저1", "안녕하세요!", color="#00ffa3")
            add_chat_message("테스트유저2", "Flet 테스트 중입니다", color="#ff9966")
            add_chat_message("후원자", "스트리머님 화이팅!", color="#ffcc00", msg_type="후원")
            add_chat_message("테스트유저3", "ㅋㅋㅋㅋㅋ", color="#66ccff")
        else:
            # 연결 해제
            connected = False
            connect_btn.content = "연결"
            connect_btn.bgcolor = "#00cc00"
            status_label.value = "연결 해제됨"
            status_label.color = ft.Colors.GREY_500
            url_input.disabled = False
            add_chat_message("시스템", "연결이 해제되었습니다.", color="#888888")

        page.update()

    # ── 상단: URL 입력 + 연결 버튼 ──
    url_input = ft.TextField(
        hint_text="스트리머 UID 또는 URL 입력",
        expand=True,
        height=40,
        text_size=13,
        border_color=ft.Colors.GREY_700,
        focused_border_color="#00ff00",
        cursor_color="#00ff00",
        on_submit=on_connect_click,
    )

    connect_btn = ft.Button(
        content="연결",
        bgcolor="#00cc00",
        color=ft.Colors.BLACK,
        height=40,
        on_click=on_connect_click,
    )

    connection_row = ft.Row(
        controls=[url_input, connect_btn],
        spacing=8,
    )

    # ── 메뉴바 (AppBar) ──
    def on_menu_click(e):
        action = e.control.data
        if action == "clear":
            chat_list.controls.clear()
            page.update()
        elif action == "settings":
            dlg = ft.AlertDialog(
                title=ft.Text("설정"),
                content=ft.Column(
                    controls=[
                        ft.Text("폰트 크기"),
                        ft.Slider(min=8, max=24, value=12, divisions=16, label="{value}pt"),
                    ],
                    tight=True,
                    spacing=10,
                ),
                actions=[
                    ft.TextButton("취소", on_click=lambda _: page.close(dlg)),
                    ft.TextButton("확인", on_click=lambda _: page.close(dlg)),
                ],
            )
            page.open(dlg)

    page.appbar = ft.AppBar(
        title=ft.Text("ChzzkChat", size=16, weight=ft.FontWeight.BOLD),
        bgcolor="#1a1a1a",
        actions=[
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(content="채팅 초기화", data="clear", on_click=on_menu_click),
                    ft.PopupMenuItem(),  # 구분선
                    ft.PopupMenuItem(content="설정", data="settings", on_click=on_menu_click),
                ],
            ),
        ],
    )

    # ── 전체 레이아웃 ──
    page.add(
        ft.Container(
            content=ft.Column(
                controls=[
                    # 연결 영역
                    ft.Container(
                        content=ft.Column(
                            controls=[connection_row, status_label],
                            spacing=4,
                        ),
                        padding=ft.Padding.all(12),
                        bgcolor="#2b2b2b",
                    ),
                    # 채팅 영역
                    ft.Container(
                        content=chat_list,
                        expand=True,
                        bgcolor="#1a1a1a",
                        padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            expand=True,
        )
    )


if __name__ == "__main__":
    ft.app(main)
