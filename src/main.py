"""ChzzkChat - Flet 앱 진입점

async def main() 사용 이유:
  Flet은 async-first 프레임워크. 백그라운드 스레드(threading.Thread)에서
  page.update()를 호출하면 UI가 실시간 갱신되지 않는 버그가 있다.
  (Flet Issue #3571, #5902 — threading.Lock으로도 해결 불가)

  해결: main()을 async로 선언하고, ChatWorker를 page.run_task()로
  Flet 이벤트 루프에서 실행. 콜백이 같은 루프에서 호출되므로
  page.update()가 즉시 UI에 반영된다.
"""

import asyncio
import hashlib
import json
import os
import re

import requests
import flet as ft

from chat_logger import ChatLogger
from chat_worker import ChatWorker
from config import COOKIES_PATH, BADGE_CACHE_DIR, EMOJI_CACHE_DIR

MAX_DISPLAY_MESSAGES = 10_000
MAX_USER_MESSAGES = 500

# ── 닉네임 색상 ──
COLOR_CODE_MAP = {
    "SG001": "#8bff00",
    "SG002": "#00ffff",
    "SG003": "#ff00ff",
    "SG004": "#ffff00",
    "SG005": "#ff8800",
    "SG006": "#ff0088",
    "SG007": "#00aaff",
    "SG008": "#aa00ff",
    "SG009": "#ff0000",
}

USER_COLOR_PALETTE = [
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#96CEB4",
    "#FFEAA7",
    "#DDA0DD",
    "#98D8C8",
    "#F7DC6F",
    "#BB8FCE",
    "#82E0AA",
    "#F1948A",
    "#85C1E9",
]


def get_user_color(uid: str, color_code: str | None) -> str:
    """닉네임 색상 결정: 프리미엄 코드 → 해시 기반 팔레트"""
    if color_code and color_code in COLOR_CODE_MAP:
        return COLOR_CODE_MAP[color_code]
    idx = abs(hash(uid)) % len(USER_COLOR_PALETTE)
    return USER_COLOR_PALETTE[idx]


# ── 이미지 캐시 ──
_badge_cache: dict[str, str | None] = {}
_emoji_cache: dict[str, str | None] = {}


def _download_image(url: str, cache_dir: str, cache_dict: dict) -> str | None:
    """URL → MD5 해시 파일명으로 로컬 캐시. 이미 있으면 즉시 반환."""
    if url in cache_dict:
        return cache_dict[url]

    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = ".gif" if ".gif" in url else ".png"
    local_path = os.path.join(cache_dir, f"{url_hash}{ext}")

    if os.path.exists(local_path):
        cache_dict[url] = local_path
        return local_path

    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            cache_dict[url] = local_path
            return local_path
    except Exception:
        pass

    cache_dict[url] = None
    return None


EMOJI_PATTERN = re.compile(r"\{:([^:]+):\}")


def extract_streamer_id(url_or_id: str) -> str:
    """URL 또는 UID에서 스트리머 ID(32자 hex) 추출"""
    url_or_id = url_or_id.strip()
    match = re.search(r"[a-f0-9]{32}", url_or_id)
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
    # 현재는 websocket 연결에 필요한 최소한의 Naver 쿠키만 요구. (NID_AUT, NID_SES)
    cookies = {}
    if os.path.exists(COOKIES_PATH):
        try:
            with open(COOKIES_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or not data:
                raise ValueError("빈 파일이거나 올바른 JSON 객체가 아닙니다")
            cookies = data
        except Exception as e:
            page.show_dialog(
                ft.SnackBar(
                    ft.Text(f"cookies.json 파싱 실패: {e}"),
                    bgcolor=ft.Colors.RED_900,
                )
            )
    else:
        page.show_dialog(
            ft.SnackBar(
                ft.Text(
                    "cookies.json 파일이 없습니다. 네이버 인증 쿠키를 설정해주세요."
                ),
                bgcolor=ft.Colors.RED_900,
            )
        )

    # ── ChatWorker 상태 ──
    worker = None
    chat_log = ChatLogger()

    # ── 채팅 메모리 ──
    all_items: list[tuple[bool, ft.Control, dict, dict]] = []  # (is_donation, widget, chat_data, refs)
    user_messages: dict[str, list] = {}  # uid → [chat_data, ...]
    donation_only = False
    at_bottom = True  # 스크롤이 맨 아래에 있는지 여부
    search_query = ""
    show_timestamp = True  # 타임스탬프 표시 여부
    show_badges = True  # 배지 표시 여부

    def _item_matches_filter(is_don: bool, cd: dict) -> bool:
        """donation_only + search_query 조합으로 표시 여부 판단"""
        if donation_only and not is_don:
            return False
        if search_query:
            q = search_query.lower()
            if (
                q not in cd.get("nickname", "").lower()
                and q not in cd.get("message", "").lower()
            ):
                return False
        return True

    def _rebuild_chat_list():
        """현재 필터(donation_only + search_query)로 visible 토글"""
        for is_don, widget, cd, _ in all_items:
            widget.visible = _item_matches_filter(is_don, cd)
        page.update()

    # ChatWorker가 page.run_task()로 같은 이벤트 루프에서 실행되므로
    # 아래 콜백에서 page.update() 호출이 안전함 (스레드 경합 없음)
    async def on_chat_received(chat_data):
        nonlocal donation_only, at_bottom, search_query
        is_donation = chat_data["type"] == "후원"
        uid = chat_data["uid"]

        # ── 유저별 메시지 추적 ──
        msgs = user_messages.setdefault(uid, [])
        msgs.append(chat_data)
        if len(msgs) > MAX_USER_MESSAGES:
            del msgs[:-MAX_USER_MESSAGES]

        # 닉네임 색상
        if is_donation:
            nick_color = "#ffcc00"
        else:
            nick_color = get_user_color(uid, chat_data.get("colorCode"))

        # 시간
        time_text = ft.Text(
            f"[{chat_data['time']}] ",
            size=13,
            color=ft.Colors.GREY_500,
            selectable=True,
            no_wrap=True,
            visible=show_timestamp,
        )

        # 배지 (최대 3개)
        badge_controls = []
        for badge_url in chat_data.get("badges", [])[:3]:
            path = await asyncio.to_thread(
                _download_image, badge_url, BADGE_CACHE_DIR, _badge_cache
            )
            if path:
                badge_controls.append(
                    ft.Image(src=path, width=18, height=18, visible=show_badges)
                )

        # 닉네임
        prefix = "[후원] " if is_donation else ""
        nick_text = ft.Text(
            f"{prefix}{chat_data['nickname']}",
            size=13,
            color=nick_color,
            weight=ft.FontWeight.BOLD,
            no_wrap=True,
        )

        # 메시지 (이모지 치환)
        message = chat_data["message"]
        emojis = chat_data.get("emojis", {})
        msg_controls = []

        if emojis:
            parts = EMOJI_PATTERN.split(message)
            # parts: [text, emoji_name, text, emoji_name, ...]
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    # 텍스트 부분
                    if part:
                        sep = ": " if i == 0 and not msg_controls else ""
                        msg_controls.append(
                            ft.Text(
                                f"{sep}{part}" if i == 0 else part,
                                size=13,
                                color=ft.Colors.WHITE,
                                selectable=True,
                            )
                        )
                else:
                    # 이모지 이름
                    if part in emojis:
                        path = await asyncio.to_thread(
                            _download_image, emojis[part], EMOJI_CACHE_DIR, _emoji_cache
                        )
                        if path:
                            msg_controls.append(ft.Image(src=path, width=20, height=20))
                            continue
                    # 매칭 실패 시 원본 텍스트
                    msg_controls.append(
                        ft.Text(
                            f"{{:{part}:}}",
                            size=13,
                            color=ft.Colors.WHITE,
                            selectable=True,
                        )
                    )
            # 첫 텍스트에 ": " 접두사
            if msg_controls and isinstance(msg_controls[0], ft.Text):
                if not msg_controls[0].value.startswith(": "):
                    msg_controls[0].value = f": {msg_controls[0].value}"
        else:
            msg_controls.append(
                ft.Text(
                    f": {message}",
                    size=13,
                    color=ft.Colors.WHITE,
                    selectable=True,
                    expand=True,
                )
            )

        # 닉네임 클릭 → UserChatDialog
        _uid, _nick = uid, chat_data["nickname"]
        nick_control = ft.GestureDetector(
            content=nick_text,
            on_tap=lambda e, u=_uid, n=_nick: show_user_dialog(u, n),
            mouse_cursor=ft.MouseCursor.CLICK,
        )

        # Row 조립: 시간 + 배지들 + 닉네임 + 메시지
        controls = [time_text] + badge_controls + [nick_control] + msg_controls

        row = ft.Row(
            controls=controls,
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        if is_donation:
            container = ft.Container(
                content=row,
                bgcolor=ft.Colors.with_opacity(0.15, "#ffcc00"),
                border_radius=4,
                padding=ft.Padding(left=4, right=4, top=2, bottom=2),
            )
            widget = container
        else:
            widget = row

        # refs: visible 토글에 사용할 컨트롤 참조
        refs = {"time": time_text, "badges": badge_controls}

        # ── 메모리 관리 ──
        all_items.append((is_donation, widget, chat_data, refs))
        if len(all_items) > MAX_DISPLAY_MESSAGES:
            _, removed_widget, _, _ = all_items.pop(0)
            chat_list.controls.remove(removed_widget)

        widget.visible = _item_matches_filter(is_donation, chat_data)
        chat_list.controls.append(widget)
        chat_log.log(chat_data)
        page.update()
        if at_bottom and widget.visible:
            await chat_list.scroll_to(offset=-1, duration=0)

    def on_status_changed(msg):
        if "연결 완료" in msg:
            status_text.color = ft.Colors.GREEN_400
            connect_btn.content.value = "해제"
            connect_btn.bgcolor = ft.Colors.RED_700
            connect_btn.disabled = False
            if worker:
                chat_log.setup(worker.channelName)
        elif "연결 실패" in msg or "재연결 실패" in msg:
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
            chat_log.close()
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

    def show_user_dialog(uid: str, nickname: str):
        """닉네임 클릭 시 유저 채팅 기록 다이얼로그"""
        msgs = user_messages.get(uid, [])

        if msgs:
            rows = []
            for cd in msgs:
                is_don = cd["type"] == "후원"
                time_ctrl = ft.Text(
                    f"[{cd['time']}]",
                    size=11,
                    color=ft.Colors.GREY_500,
                    no_wrap=True,
                )
                prefix = "[후원] " if is_don else ""
                msg_ctrl = ft.Text(
                    f"{prefix}{cd['message']}",
                    size=12,
                    color=ft.Colors.AMBER_300 if is_don else ft.Colors.WHITE,
                    selectable=True,
                    expand=True,
                )
                row = ft.Row(
                    controls=[time_ctrl, msg_ctrl],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
                if is_don:
                    item = ft.Container(
                        content=row,
                        bgcolor=ft.Colors.with_opacity(0.15, "#ffcc00"),
                        border_radius=4,
                        padding=ft.Padding(left=4, right=4, top=2, bottom=2),
                    )
                else:
                    item = row
                rows.append(item)
            list_content = ft.ListView(
                controls=rows,
                spacing=2,
                auto_scroll=True,
                padding=ft.Padding.symmetric(horizontal=4, vertical=2),
            )
        else:
            list_content = ft.Text("채팅 기록 없음", color=ft.Colors.GREY_500, size=12)

        count_label = ft.Text(
            f"최근 {len(msgs)}건" if msgs else "",
            size=11,
            color=ft.Colors.GREY_600,
        )

        dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Text(nickname, weight=ft.FontWeight.BOLD),
                    count_label,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=list_content,
                width=400,
                height=300,
                border=ft.Border.all(1, ft.Colors.GREY_800),
                border_radius=4,
                bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            ),
            actions=[
                ft.TextButton(
                    "닫기",
                    on_click=lambda e: (setattr(dialog, "open", False), page.update()),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    def toggle_timestamp(e):
        nonlocal show_timestamp
        show_timestamp = not show_timestamp
        timestamp_menu_item.content.value = "타임스탬프 ✓" if show_timestamp else "타임스탬프"
        for _, _, _, refs in all_items:
            refs["time"].visible = show_timestamp
        page.update()

    def toggle_badges(e):
        nonlocal show_badges
        show_badges = not show_badges
        badge_menu_item.content.value = "배지 ✓" if show_badges else "배지"
        for _, _, _, refs in all_items:
            for badge in refs["badges"]:
                badge.visible = show_badges
        page.update()

    def toggle_donation_only(e):
        nonlocal donation_only
        donation_only = not donation_only
        donation_menu_item.content.value = (
            "후원만 보기 ✓" if donation_only else "후원만 보기"
        )
        _rebuild_chat_list()

    def clear_chat(e):
        nonlocal search_query
        all_items.clear()
        user_messages.clear()
        chat_list.controls.clear()
        search_query = ""
        search_field.value = ""
        page.update()

    def toggle_search(e=None):
        nonlocal search_query
        search_row.visible = not search_row.visible
        if search_row.visible:
            search_field.focus()
        else:
            search_query = ""
            search_field.value = ""
            _rebuild_chat_list()
        page.update()

    def on_search_changed(e):
        nonlocal search_query
        search_query = search_field.value or ""
        _rebuild_chat_list()

    async def on_keyboard_event(e: ft.KeyboardEvent):
        if e.ctrl and e.key == "F":
            toggle_search()

    page.on_keyboard_event = on_keyboard_event

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

    # ── 검색 바 (Ctrl+F로 토글) ──
    search_field = ft.TextField(
        hint_text="닉네임 또는 메시지 검색...",
        expand=True,
        height=36,
        border_color=ft.Colors.GREY_700,
        focused_border_color=ft.Colors.BLUE_400,
        text_size=13,
        on_change=on_search_changed,
    )

    search_row = ft.Row(
        controls=[
            ft.Icon(ft.Icons.SEARCH, size=16, color=ft.Colors.GREY_500),
            search_field,
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_size=16,
                tooltip="검색 닫기 (Esc)",
                on_click=toggle_search,
            ),
        ],
        spacing=4,
        visible=False,
    )

    def on_chat_list_scroll(e: ft.OnScrollEvent):
        nonlocal at_bottom
        at_bottom = e.pixels >= e.max_scroll_extent - 10

    # ── 채팅 표시 영역 ──
    chat_list = ft.ListView(
        expand=True,
        spacing=2,
        auto_scroll=False,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        on_scroll=on_chat_list_scroll,
    )

    chat_container = ft.Container(
        content=chat_list,
        expand=True,
        border=ft.Border.all(1, ft.Colors.GREY_800),
        border_radius=4,
        bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
    )

    # ── 메뉴바 ──
    donation_menu_item = ft.MenuItemButton(
        content=ft.Text("후원만 보기"),
        leading=ft.Icon(ft.Icons.VOLUNTEER_ACTIVISM, size=18),
        on_click=toggle_donation_only,
    )

    timestamp_menu_item = ft.MenuItemButton(
        content=ft.Text("타임스탬프 ✓"),
        leading=ft.Icon(ft.Icons.ACCESS_TIME, size=18),
        on_click=toggle_timestamp,
    )

    badge_menu_item = ft.MenuItemButton(
        content=ft.Text("배지 ✓"),
        leading=ft.Icon(ft.Icons.MILITARY_TECH, size=18),
        on_click=toggle_badges,
    )

    menubar = ft.MenuBar(
        controls=[
            ft.SubmenuButton(
                content=ft.Text("옵션", size=13),
                controls=[
                    donation_menu_item,
                    ft.MenuItemButton(
                        content=ft.Text("채팅 내역 초기화"),
                        leading=ft.Icon(ft.Icons.DELETE_SWEEP, size=18),
                        on_click=clear_chat,
                    ),
                    ft.Divider(height=1),
                    ft.MenuItemButton(
                        content=ft.Text("종료"),
                        leading=ft.Icon(ft.Icons.EXIT_TO_APP, size=18),
                        on_click=lambda e: page.window.close(),
                    ),
                ],
            ),
            ft.SubmenuButton(
                content=ft.Text("설정", size=13),
                controls=[
                    timestamp_menu_item,
                    badge_menu_item,
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
                            search_row,
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
