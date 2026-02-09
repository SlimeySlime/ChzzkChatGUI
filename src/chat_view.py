"""
ChzzkChat 메인 채팅 UI (Flet)
"""
import re
import os
import json
import hashlib
import logging

from collections import defaultdict

import flet as ft
import requests

from config import (
    BADGE_CACHE_DIR, EMOJI_CACHE_DIR,
    SETTINGS_PATH, BUG_REPORT_EMAIL
)
from chat_worker import ChatWorker
from chat_logger import ChatLogger

logger = logging.getLogger(__name__)

# 치지직 colorCode 매핑 (프리미엄 색상)
COLOR_CODE_MAP = {
    'SG001': '#8bff00',
    'SG002': '#00ffff',
    'SG003': '#ff00ff',
    'SG004': '#ffff00',
    'SG005': '#ff8800',
    'SG006': '#ff0088',
    'SG007': '#00aaff',
    'SG008': '#aa00ff',
    'SG009': '#ff0000',
}

# 일반 유저 색상 팔레트
USER_COLOR_PALETTE = [
    '#00ffa3', '#ff9966', '#66ccff', '#cc99ff',
    '#ff6699', '#99ff99', '#ffcc66', '#66ffcc',
    '#ff6666', '#99ccff', '#ffff66', '#ff99cc',
]


def get_user_color(uid, color_code):
    """uid/colorCode 기반 닉네임 색상"""
    if color_code and color_code in COLOR_CODE_MAP:
        return COLOR_CODE_MAP[color_code]
    return USER_COLOR_PALETTE[abs(hash(uid)) % len(USER_COLOR_PALETTE)]


def extract_streamer_id(url_or_id):
    """URL 또는 UID에서 32자 hex 스트리머 ID 추출"""
    url_or_id = url_or_id.strip()
    match = re.search(r'[a-f0-9]{32}', url_or_id)
    if match:
        return match.group(0)
    return url_or_id


class ChzzkChatApp:
    """Flet 기반 채팅 앱"""

    MAX_DISPLAY_MESSAGES = 10000
    MAX_USER_MESSAGES = 500

    def __init__(self, page: ft.Page, cookies: dict):
        self.page = page
        self.cookies = cookies
        self.worker = None
        self.is_connected = False
        self.streamer = None

        # 상태
        self.user_messages = defaultdict(list)
        self.user_nicknames = {}
        self.all_messages = []       # (chat_type, container) 전체 메시지
        self.badge_cache = {}
        self.emoji_cache = {}
        self.donation_only = False
        self.chat_logger = None
        self.settings = self._load_settings()

        # 검색
        self.search_matches = []
        self.search_match_index = 0
        self.search_visible = False

    def _load_settings(self):
        default = {'font_size': 12}
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    return {**default, **json.load(f)}
        except Exception:
            logger.warning('설정 로드 실패', exc_info=True)
        return default

    def _save_settings(self):
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.warning('설정 저장 실패', exc_info=True)

    # ── 배지/이모지 캐시 ──
    def _get_cached_image(self, url, cache_dir):
        if not url:
            return None
        cache_key = f"{cache_dir}:{url}"
        if cache_key in self.badge_cache:
            return self.badge_cache[cache_key]
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            ext = '.gif' if '.gif' in url else '.png'
            local_path = os.path.join(cache_dir, f'{url_hash}{ext}')
            if os.path.exists(local_path):
                self.badge_cache[cache_key] = local_path
                return local_path
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                self.badge_cache[cache_key] = local_path
                return local_path
        except Exception:
            logger.debug('이미지 캐시 실패: %s', url, exc_info=True)
        return None

    def get_badge_path(self, url):
        return self._get_cached_image(url, BADGE_CACHE_DIR)

    def get_emoji_path(self, url):
        return self._get_cached_image(url, EMOJI_CACHE_DIR)

    # ── 이모지 처리 → Text/Image 컨트롤 리스트 ──
    def _build_message_controls(self, message, emojis, font_size):
        """메시지 텍스트를 Text/Image 세그먼트 리스트로 변환"""
        if not emojis:
            return [ft.Text(message, size=font_size, color=ft.Colors.WHITE)]

        controls = []
        pattern = r'\{:([^:]+):\}'
        last_end = 0

        for match in re.finditer(pattern, message):
            # 이모지 앞의 텍스트
            if match.start() > last_end:
                controls.append(ft.Text(
                    message[last_end:match.start()],
                    size=font_size, color=ft.Colors.WHITE,
                ))

            emoji_name = match.group(1)
            if emoji_name in emojis:
                emoji_url = emojis[emoji_name]
                emoji_path = self.get_emoji_path(emoji_url)
                if emoji_path:
                    controls.append(ft.Image(
                        src=emoji_path, width=20, height=20,
                        fit=ft.ImageFit.CONTAIN,
                    ))
                else:
                    # URL 직접 사용
                    controls.append(ft.Image(
                        src=emoji_url, width=20, height=20,
                        fit=ft.ImageFit.CONTAIN,
                    ))
            else:
                controls.append(ft.Text(
                    match.group(0), size=font_size, color=ft.Colors.WHITE,
                ))

            last_end = match.end()

        # 남은 텍스트
        if last_end < len(message):
            controls.append(ft.Text(
                message[last_end:], size=font_size, color=ft.Colors.WHITE,
            ))

        return controls if controls else [ft.Text(message, size=font_size, color=ft.Colors.WHITE)]

    # ── UI 빌드 ──
    def build(self):
        page = self.page
        page.title = "ChzzkChat"
        page.theme_mode = ft.ThemeMode.DARK
        page.window.width = 500
        page.window.height = 700
        page.padding = 0

        font_size = self.settings.get('font_size', 12)

        # 채팅 리스트
        self.chat_list = ft.ListView(
            expand=True, spacing=2, auto_scroll=True,
        )

        # 상태 라벨
        self.status_label = ft.Text(
            "스트리머 주소를 입력하고 연결 버튼을 눌러주세요",
            size=11, color=ft.Colors.GREY_500,
        )

        # URL 입력
        self.url_input = ft.TextField(
            hint_text="스트리머 UID 또는 URL 입력",
            expand=True, height=40, text_size=13,
            border_color=ft.Colors.GREY_700,
            focused_border_color="#00ff00",
            cursor_color="#00ff00",
            on_submit=self._on_connect_click,
        )

        # 연결 버튼
        self.connect_btn = ft.Button(
            content="연결",
            bgcolor="#00cc00", color=ft.Colors.BLACK,
            height=40,
            on_click=self._on_connect_click,
        )

        # 검색 바
        self.search_input = ft.TextField(
            hint_text="검색...", expand=True, height=36, text_size=12,
            border_color=ft.Colors.GREY_700,
            focused_border_color="#00ff00",
            on_change=self._on_search_changed,
            on_submit=self._on_search_next,
        )
        self.search_count_label = ft.Text("", size=11, color="#888888")
        self.search_bar = ft.Container(
            content=ft.Row(
                controls=[
                    self.search_input,
                    ft.IconButton(ft.Icons.ARROW_UPWARD, icon_size=16, on_click=self._on_search_prev),
                    ft.IconButton(ft.Icons.ARROW_DOWNWARD, icon_size=16, on_click=self._on_search_next),
                    self.search_count_label,
                    ft.IconButton(ft.Icons.CLOSE, icon_size=16, on_click=self._close_search),
                ],
                spacing=4,
            ),
            padding=ft.Padding(5, 2, 5, 2),
            visible=False,
        )

        # 메뉴
        def on_menu_click(e):
            action = e.control.data
            if action == "donation_only":
                self.donation_only = not self.donation_only
                self._rerender_chat()
            elif action == "clear":
                self._clear_chat()
            elif action == "settings":
                self._open_settings()
            elif action == "bug_report":
                self._open_bug_report()

        page.appbar = ft.AppBar(
            title=ft.Text("ChzzkChat", size=16, weight=ft.FontWeight.BOLD),
            bgcolor="#1a1a1a",
            actions=[
                ft.PopupMenuButton(
                    items=[
                        ft.PopupMenuItem(content="후원만 보기", data="donation_only", on_click=on_menu_click),
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(content="채팅 초기화", data="clear", on_click=on_menu_click),
                        ft.PopupMenuItem(),
                        ft.PopupMenuItem(content="설정", data="settings", on_click=on_menu_click),
                        ft.PopupMenuItem(content="버그 리포트", data="bug_report", on_click=on_menu_click),
                    ],
                ),
            ],
        )

        # 키보드 이벤트 (Ctrl+F)
        page.on_keyboard_event = self._on_keyboard

        # 레이아웃
        page.add(
            ft.Container(
                content=ft.Column(
                    controls=[
                        # 연결 영역
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[self.url_input, self.connect_btn],
                                        spacing=8,
                                    ),
                                    self.status_label,
                                ],
                                spacing=4,
                            ),
                            padding=ft.Padding.all(12),
                            bgcolor="#2b2b2b",
                        ),
                        # 채팅 영역
                        ft.Container(
                            content=self.chat_list,
                            expand=True,
                            bgcolor="#1a1a1a",
                            padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                        ),
                        # 검색 바
                        self.search_bar,
                    ],
                    spacing=0,
                    expand=True,
                ),
                expand=True,
            )
        )

    # ── 연결/해제 ──
    def _on_connect_click(self, e):
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        url_or_id = self.url_input.value.strip()
        if not url_or_id:
            self.status_label.value = "UID 또는 URL을 입력하세요"
            self.status_label.color = ft.Colors.RED_400
            self.page.update()
            return

        if self.worker:
            self.worker.stop()

        self.streamer = extract_streamer_id(url_or_id)
        self.url_input.disabled = True
        self.connect_btn.disabled = True
        self.page.update()

        self.worker = ChatWorker(
            self.streamer, self.cookies,
            on_chat_received=self._on_chat_received,
            on_status_changed=self._on_status_changed,
        )
        self.worker.start()

    def _disconnect(self):
        if self.worker:
            self.worker.stop()
            self.worker = None

        self.is_connected = False
        self.connect_btn.content = "연결"
        self.connect_btn.bgcolor = "#00cc00"
        self.connect_btn.color = ft.Colors.BLACK
        self.url_input.disabled = False
        self.status_label.value = "연결이 해제되었습니다."
        self.status_label.color = ft.Colors.GREY_500
        self.page.update()

    # ── ChatWorker 콜백 (워커 스레드에서 호출) ──
    def _on_status_changed(self, status):
        self.status_label.value = status
        if '완료' in status:
            self.status_label.color = "#00ff00"
            self.is_connected = True
            self.connect_btn.content = "연결 해제"
            self.connect_btn.bgcolor = "#cc0000"
            self.connect_btn.color = ft.Colors.WHITE
            self.connect_btn.disabled = False
            # 로거 초기화
            if self.worker and self.worker.channelName:
                self.chat_logger = ChatLogger(self.worker.channelName)
        elif '실패' in status:
            self.status_label.color = ft.Colors.RED_400
            self.is_connected = False
            self.connect_btn.content = "연결"
            self.connect_btn.bgcolor = "#00cc00"
            self.connect_btn.color = ft.Colors.BLACK
            self.connect_btn.disabled = False
            self.url_input.disabled = False
        else:
            self.status_label.color = "#ffcc00"
        self.page.update()

    def _on_chat_received(self, chat_data):
        uid = chat_data['uid']
        nickname = chat_data['nickname']
        message = chat_data['message']
        chat_type = chat_data['type']
        time_str = chat_data['time']
        color_code = chat_data.get('colorCode')
        badges = chat_data.get('badges', [])
        emojis = chat_data.get('emojis', {})

        font_size = self.settings.get('font_size', 12)

        # 유저별 메시지 저장
        user_msgs = self.user_messages[uid]
        user_msgs.append({'time': time_str, 'type': chat_type, 'message': message})
        if len(user_msgs) > self.MAX_USER_MESSAGES:
            del user_msgs[:len(user_msgs) - self.MAX_USER_MESSAGES]
        self.user_nicknames[uid] = nickname

        # 로그 기록
        if self.chat_logger:
            self.chat_logger.log(time_str, chat_type, nickname, uid, message)

        # 닉네임 색상
        if chat_type == '후원':
            nick_color = '#ffcc00'
            prefix = '[후원] '
            bg_color = "#3d3d00"
        else:
            nick_color = get_user_color(uid, color_code)
            prefix = ''
            bg_color = None

        # 배지 컨트롤
        badge_controls = []
        for badge_url in badges[:3]:
            badge_path = self.get_badge_path(badge_url)
            src = badge_path if badge_path else badge_url
            badge_controls.append(ft.Image(
                src=src, width=18, height=18, fit=ft.ImageFit.CONTAIN,
            ))

        # 메시지 컨트롤 (이모지 포함)
        msg_controls = self._build_message_controls(message, emojis, font_size)

        # 닉네임 (클릭 가능)
        nickname_text = ft.Text(
            f"{prefix}{nickname}",
            size=font_size, color=nick_color,
            weight=ft.FontWeight.BOLD,
            data=uid,
        )
        nickname_container = ft.GestureDetector(
            content=nickname_text,
            on_tap=lambda e, _uid=uid: self._on_user_clicked(_uid),
        )

        # Row 조합
        row_controls = [
            ft.Text(f"[{time_str}]", size=font_size - 1, color="#888888"),
            *badge_controls,
            nickname_container,
            *msg_controls,
        ]

        msg_container = ft.Container(
            content=ft.Row(
                controls=row_controls,
                spacing=6,
                wrap=True,
            ),
            bgcolor=bg_color,
            padding=ft.Padding(6, 4, 6, 4),
            border_radius=3,
            data={'uid': uid, 'nickname': nickname, 'message': message, 'type': chat_type},
        )

        # 전체 메시지 기록
        self.all_messages.append((chat_type, msg_container))
        if len(self.all_messages) > self.MAX_DISPLAY_MESSAGES:
            del self.all_messages[:len(self.all_messages) - self.MAX_DISPLAY_MESSAGES]

        # 후원 전용 모드: 후원이 아니면 표시 스킵
        if self.donation_only and chat_type != '후원':
            return

        self.chat_list.controls.append(msg_container)

        # 표시 메시지 수 제한
        overflow = len(self.chat_list.controls) - self.MAX_DISPLAY_MESSAGES
        if overflow > 0:
            del self.chat_list.controls[:overflow]

        self.page.update()

    # ── 유저 클릭 ──
    def _on_user_clicked(self, uid):
        if uid not in self.user_nicknames:
            return
        nickname = self.user_nicknames[uid]
        messages = self.user_messages[uid]

        msg_controls = []
        for msg in messages:
            msg_color = '#ffcc00' if msg['type'] == '후원' else ft.Colors.WHITE
            msg_controls.append(ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(f"[{msg['time']}]", size=11, color="#888888"),
                        ft.Text(msg['message'], size=12, color=msg_color),
                    ],
                    spacing=6, wrap=True,
                ),
                bgcolor="#252525",
                padding=ft.Padding.all(5),
                border_radius=3,
            ))

        dlg = ft.AlertDialog(
            title=ft.Column(
                controls=[
                    ft.Text(nickname, size=16, weight=ft.FontWeight.BOLD, color="#00ff00"),
                    ft.Text(f"UID: {uid}", size=11, color="#666666"),
                    ft.Text(f"총 {len(messages)}개의 메시지", size=12, color="#888888"),
                ],
                spacing=2, tight=True,
            ),
            content=ft.Container(
                content=ft.ListView(
                    controls=msg_controls,
                    spacing=2,
                ),
                width=400, height=350,
            ),
            actions=[
                ft.TextButton("닫기", on_click=lambda _: self.page.close(dlg)),
            ],
        )
        self.page.open(dlg)

    # ── 채팅 초기화 ──
    def _clear_chat(self):
        self.chat_list.controls.clear()
        self.all_messages.clear()
        self.user_messages.clear()
        self.user_nicknames.clear()
        self.page.update()

    # ── 후원 전용 모드 재렌더링 ──
    def _rerender_chat(self):
        self.chat_list.controls.clear()
        for chat_type, container in self.all_messages:
            if not self.donation_only or chat_type == '후원':
                self.chat_list.controls.append(container)
        self.page.update()

    # ── 검색 ──
    def _on_keyboard(self, e: ft.KeyboardEvent):
        if e.ctrl and e.key == "F":
            self._toggle_search()

    def _toggle_search(self):
        self.search_visible = not self.search_visible
        self.search_bar.visible = self.search_visible
        if self.search_visible:
            self.search_input.focus()
        else:
            self._clear_search_highlights()
        self.page.update()

    def _close_search(self, e=None):
        self.search_visible = False
        self.search_bar.visible = False
        self._clear_search_highlights()
        self.page.update()

    def _clear_search_highlights(self):
        for _, container in self.all_messages:
            if hasattr(container, '_original_bgcolor'):
                container.bgcolor = container._original_bgcolor
        self.search_matches.clear()
        self.search_match_index = 0
        self.search_count_label.value = ""

    def _on_search_changed(self, e):
        text = self.search_input.value.strip().lower()
        self._clear_search_highlights()

        if not text:
            self.page.update()
            return

        self.search_matches = []
        for _, container in self.all_messages:
            data = container.data
            if data and text in data.get('message', '').lower() or \
               data and text in data.get('nickname', '').lower():
                if not hasattr(container, '_original_bgcolor'):
                    container._original_bgcolor = container.bgcolor
                self.search_matches.append(container)

        if self.search_matches:
            self.search_match_index = 0
            self._highlight_current_match()
            self.search_count_label.value = f"1/{len(self.search_matches)}"
        else:
            self.search_count_label.value = "0건"

        self.page.update()

    def _highlight_current_match(self):
        for i, container in enumerate(self.search_matches):
            if i == self.search_match_index:
                container.bgcolor = "#665500"
            else:
                container.bgcolor = "#333300"

    def _on_search_next(self, e=None):
        if not self.search_matches:
            return
        self.search_match_index = (self.search_match_index + 1) % len(self.search_matches)
        self._highlight_current_match()
        self.search_count_label.value = f"{self.search_match_index + 1}/{len(self.search_matches)}"
        # scroll to match
        target = self.search_matches[self.search_match_index]
        target.update()
        self.page.update()

    def _on_search_prev(self, e=None):
        if not self.search_matches:
            return
        self.search_match_index = (self.search_match_index - 1) % len(self.search_matches)
        self._highlight_current_match()
        self.search_count_label.value = f"{self.search_match_index + 1}/{len(self.search_matches)}"
        target = self.search_matches[self.search_match_index]
        target.update()
        self.page.update()

    # ── 설정 ──
    def _open_settings(self):
        font_slider = ft.Slider(
            min=8, max=24,
            value=self.settings.get('font_size', 12),
            divisions=16, label="{value}pt",
        )

        def on_save(e):
            self.settings['font_size'] = int(font_slider.value)
            self._save_settings()
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("설정"),
            content=ft.Column(
                controls=[
                    ft.Text("채팅 폰트 크기"),
                    font_slider,
                ],
                tight=True, spacing=10,
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.close(dlg)),
                ft.TextButton("확인", on_click=on_save),
            ],
        )
        self.page.open(dlg)

    # ── 버그 리포트 ──
    def _open_bug_report(self):
        if not BUG_REPORT_EMAIL:
            dlg = ft.AlertDialog(
                title=ft.Text("알림"),
                content=ft.Text(".env 파일에 BUG_REPORT_EMAIL을 설정해주세요."),
                actions=[ft.TextButton("확인", on_click=lambda _: self.page.close(dlg))],
            )
            self.page.open(dlg)
            return

        import platform
        import sys
        from urllib.parse import quote

        title_input = ft.TextField(hint_text="버그 제목", expand=True)
        desc_input = ft.TextField(
            hint_text="어떤 상황에서 버그가 발생했나요?",
            multiline=True, min_lines=3, max_lines=6,
        )
        sys_info = f'OS: {platform.system()} {platform.release()}, Python: {sys.version.split()[0]}'

        def on_send(e):
            title = title_input.value.strip()
            if not title:
                return
            desc = desc_input.value.strip()
            subject = f'[ChzzkChat Bug] {title}'
            body = f'{desc}\n\n---\n{sys_info}'
            mailto = f'mailto:{BUG_REPORT_EMAIL}?subject={quote(subject)}&body={quote(body)}'
            self.page.launch_url(mailto)
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("버그 리포트"),
            content=ft.Column(
                controls=[
                    ft.Text("제목"),
                    title_input,
                    ft.Text("설명"),
                    desc_input,
                    ft.Text(sys_info, size=11, color="#666666"),
                ],
                tight=True, spacing=8, width=400,
            ),
            actions=[
                ft.TextButton("취소", on_click=lambda _: self.page.close(dlg)),
                ft.TextButton("메일 전송", on_click=on_send),
            ],
        )
        self.page.open(dlg)
