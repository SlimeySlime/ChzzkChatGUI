"""ChzzkChat - Flet 앱 진입점

async def main() 사용 이유:
  Flet은 async-first 프레임워크. 백그라운드 스레드(threading.Thread)에서
  page.update()를 호출하면 UI가 실시간 갱신되지 않는 버그가 있다.
  (Flet Issue #3571, #5902 — threading.Lock으로도 해결 불가)

  해결: main()을 async로 선언하고, ChatWorker를 page.run_task()로
  Flet 이벤트 루프에서 실행. 콜백이 같은 루프에서 호출되므로
  page.update()가 즉시 UI에 반영된다.
"""

import json
import os
import re

import flet as ft

from chat_worker import ChatWorker
from config import COOKIES_PATH

# ── 닉네임 색상 ──
COLOR_CODE_MAP = {
    'SG001': '#8bff00', 'SG002': '#00ffff', 'SG003': '#ff00ff',
    'SG004': '#ffff00', 'SG005': '#ff8800', 'SG006': '#ff0088',
    'SG007': '#00aaff', 'SG008': '#aa00ff', 'SG009': '#ff0000',
}

USER_COLOR_PALETTE = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
    '#BB8FCE', '#82E0AA', '#F1948A', '#85C1E9',
]


def get_user_color(uid: str, color_code: str | None) -> str:
    """닉네임 색상 결정: 프리미엄 코드 → 해시 기반 팔레트"""
    if color_code and color_code in COLOR_CODE_MAP:
        return COLOR_CODE_MAP[color_code]
    idx = abs(hash(uid)) % len(USER_COLOR_PALETTE)
    return USER_COLOR_PALETTE[idx]


def extract_streamer_id(url_or_id: str) -> str:
    """URL 또는 UID에서 스트리머 ID(32자 hex) 추출"""
    url_or_id = url_or_id.strip()
    match = re.search(r'[a-f0-9]{32}', url_or_id)
    if match:
        return match.group(0)
    return url_or_id


async def main(page: ft.Page):
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
                data = json.load(f)
            if not isinstance(data, dict) or not data:
                raise ValueError("빈 파일이거나 올바른 JSON 객체가 아닙니다")
            cookies = data
        except Exception as e:
            page.show_dialog(ft.SnackBar(
                ft.Text(f"cookies.json 파싱 실패: {e}"),
                bgcolor=ft.Colors.RED_900,
            ))
    else:
        page.show_dialog(ft.SnackBar(
            ft.Text("cookies.json 파일이 없습니다. 네이버 인증 쿠키를 설정해주세요."),
            bgcolor=ft.Colors.RED_900,
        ))

    # ── ChatWorker 상태 ──
    worker = None

    # ChatWorker가 page.run_task()로 같은 이벤트 루프에서 실행되므로
    # 아래 콜백에서 page.update() 호출이 안전함 (스레드 경합 없음)
    def on_chat_received(chat_data):
        is_donation = chat_data['type'] == '후원'

        # 닉네임 색상
        if is_donation:
            nick_color = '#ffcc00'
        else:
            nick_color = get_user_color(chat_data['uid'], chat_data.get('colorCode'))

        # 시간
        time_text = ft.Text(
            f"[{chat_data['time']}] ",
            size=13,
            color=ft.Colors.GREY_500,
            selectable=True,
            no_wrap=True,
        )

        # 닉네임
        prefix = "[후원] " if is_donation else ""
        nick_text = ft.Text(
            f"{prefix}{chat_data['nickname']}",
            size=13,
            color=nick_color,
            weight=ft.FontWeight.BOLD,
            selectable=True,
            no_wrap=True,
        )

        # 메시지
        msg_text = ft.Text(
            f": {chat_data['message']}",
            size=13,
            color=ft.Colors.WHITE,
            selectable=True,
            expand=True,
        )

        # 후원 메시지 배경
        row = ft.Row(
            controls=[time_text, nick_text, msg_text],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        if is_donation:
            container = ft.Container(
                content=row,
                bgcolor=ft.Colors.with_opacity(0.15, '#ffcc00'),
                border_radius=4,
                padding=ft.Padding(left=4, right=4, top=2, bottom=2),
            )
            widget = container
        else:
            widget = row

        chat_list.controls.append(widget)
        page.update()

    def on_status_changed(msg):
        if '연결 완료' in msg:
            status_text.color = ft.Colors.GREEN_400
            connect_btn.content.value = "해제"
            connect_btn.bgcolor = ft.Colors.RED_700
            connect_btn.disabled = False
        elif '연결 실패' in msg or '재연결 실패' in msg:
            status_text.color = ft.Colors.RED_400
            connect_btn.content.value = "연결"
            connect_btn.bgcolor = ft.Colors.GREEN
            connect_btn.disabled = False
            url_input.disabled = False
        else:
            status_text.color = ft.Colors.YELLOW_400
        status_text.value = msg
        page.update()

    async def on_connect_clicked(e):
        nonlocal worker

        # 해제 모드
        if worker and worker.running:
            await worker.stop()
            worker = None
            connect_btn.content.value = "연결"
            connect_btn.bgcolor = ft.Colors.GREEN
            connect_btn.disabled = False
            url_input.disabled = False
            status_text.value = "연결 해제됨"
            status_text.color = ft.Colors.GREY_500
            page.update()
            return

        # 연결 모드
        raw = url_input.value or ""
        uid = extract_streamer_id(raw)
        if not uid:
            status_text.value = "스트리머 주소를 입력해주세요"
            status_text.color = ft.Colors.RED_400
            page.update()
            return

        connect_btn.disabled = True
        connect_btn.content.value = "연결 중..."
        url_input.disabled = True
        status_text.value = "채팅 서버에 연결 중..."
        status_text.color = ft.Colors.YELLOW_400
        page.update()

        worker = ChatWorker(uid, cookies, on_chat_received, on_status_changed)
        page.run_task(worker.run)  # Flet 이벤트 루프에서 async 실행

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
        on_click=on_connect_clicked,
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
