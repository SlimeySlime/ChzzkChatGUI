"""
메인 UI 윈도우
"""
import os
import json
import datetime
import logging
import hashlib
import re
import requests

from collections import defaultdict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSystemTrayIcon, QMenu,
    QDialog, QGraphicsOpacityEffect, QApplication
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QIcon, QAction

from src.config import (
    BASE_DIR, BADGE_CACHE_DIR, EMOJI_CACHE_DIR,
    LOG_DIR, SETTINGS_PATH, ICON_PATH, API_SERVER_URL, API_KEY
)
from src.workers import ChatWorker
from src.dialogs import SettingsDialog, UserChatDialog
from src.widgets import ClickableTextEdit


class ChzzkChatUI(QMainWindow):
    """메인 UI 윈도우"""

    # 치지직 colorCode 매핑 테이블 (프리미엄 색상)
    COLOR_CODE_MAP = {
        'SG001': '#8bff00',  # 연두
        'SG002': '#00ffff',  # 시안
        'SG003': '#ff00ff',  # 마젠타
        'SG004': '#ffff00',  # 노랑
        'SG005': '#ff8800',  # 주황
        'SG006': '#ff0088',  # 핑크
        'SG007': '#00aaff',  # 파랑
        'SG008': '#aa00ff',  # 보라
        'SG009': '#ff0000',  # 빨강
    }

    # 일반 유저용 색상 팔레트
    USER_COLOR_PALETTE = [
        '#00ffa3',  # 민트
        '#ff9966',  # 주황
        '#66ccff',  # 하늘
        '#cc99ff',  # 보라
        '#ff6699',  # 핑크
        '#99ff99',  # 연두
        '#ffcc66',  # 골드
        '#66ffcc',  # 청록
        '#ff6666',  # 빨강
        '#99ccff',  # 파랑
        '#ffff66',  # 노랑
        '#ff99cc',  # 연핑크
    ]

    def __init__(self, cookies):
        super().__init__()
        self.streamer = None
        self.cookies = cookies
        self.worker = None
        self.is_connected = False
        self.user_messages = defaultdict(list)
        self.user_nicknames = {}
        self.chat_logger = None
        self.log_channel_name = None
        self.current_log_date = None
        self.badge_cache = {}
        self.emoji_cache = {}
        self.settings = self.load_settings()

        # 서버 배치 전송용 버퍼
        self.chat_buffer = []
        self.batch_timer = QTimer()
        self.batch_timer.timeout.connect(self.send_batch_to_server)
        self.batch_timer.start(60000)  # 1분마다 전송

        self.init_ui()
        self.init_tray_icon()

    def get_user_color(self, uid, color_code):
        """uid와 colorCode 기반으로 닉네임 색상 반환"""
        if color_code and color_code in self.COLOR_CODE_MAP:
            return self.COLOR_CODE_MAP[color_code]
        hash_value = hash(uid)
        color_index = abs(hash_value) % len(self.USER_COLOR_PALETTE)
        return self.USER_COLOR_PALETTE[color_index]

    def get_badge_path(self, url):
        """배지 이미지 URL을 로컬 캐시 경로로 변환"""
        if not url:
            return None

        if url in self.badge_cache:
            return self.badge_cache[url]

        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            ext = os.path.splitext(url)[1] or '.png'
            local_path = os.path.join(BADGE_CACHE_DIR, f'{url_hash}{ext}')

            if os.path.exists(local_path):
                self.badge_cache[url] = local_path
                return local_path

            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                self.badge_cache[url] = local_path
                return local_path
        except:
            pass

        return None

    def get_emoji_path(self, url):
        """이모지 이미지 URL을 로컬 캐시 경로로 변환"""
        if not url:
            return None

        if url in self.emoji_cache:
            return self.emoji_cache[url]

        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            if '.gif' in url:
                ext = '.gif'
            elif '.png' in url:
                ext = '.png'
            else:
                ext = '.png'
            local_path = os.path.join(EMOJI_CACHE_DIR, f'{url_hash}{ext}')

            if os.path.exists(local_path):
                self.emoji_cache[url] = local_path
                return local_path

            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                self.emoji_cache[url] = local_path
                return local_path
        except:
            pass

        return None

    def process_message_emojis(self, message, emojis):
        """메시지 내 이모지 코드를 이미지 HTML로 치환"""
        if not emojis:
            return message

        pattern = r'\{:([^:]+):\}'

        def replace_emoji(match):
            emoji_name = match.group(1)
            if emoji_name in emojis:
                emoji_url = emojis[emoji_name]
                emoji_path = self.get_emoji_path(emoji_url)
                if emoji_path:
                    return f'<img src="file:///{emoji_path.replace(os.sep, "/")}" width="20" height="20" style="vertical-align: middle;"/>'
            return match.group(0)

        return re.sub(pattern, replace_emoji, message)

    def load_settings(self):
        """설정 파일 로드"""
        default_settings = {
            'font_size': 10,
            'window_width': 500,
            'window_height': 600
        }
        try:
            if os.path.exists(SETTINGS_PATH):
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    return {**default_settings, **json.load(f)}
        except:
            pass
        return default_settings

    def save_settings(self):
        """설정 파일 저장"""
        try:
            with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except:
            pass

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle('Chzzk Chat')
        # 저장된 창 크기 복원
        width = self.settings.get('window_width', 500)
        height = self.settings.get('window_height', 600)
        self.setGeometry(100, 100, width, height)

        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        # 메뉴바 설정
        menubar = self.menuBar()
        menubar.setStyleSheet('''
            QMenuBar {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QMenuBar::item:selected {
                background-color: #3d3d3d;
            }
            QMenu {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
        ''')

        # 옵션 메뉴
        option_menu = menubar.addMenu('옵션')
        quit_action = QAction('종료', self)
        quit_action.triggered.connect(self.quit_app)
        option_menu.addAction(quit_action)

        # 설정 메뉴
        setting_menu = menubar.addMenu('설정')
        setting_action = QAction('설정 열기', self)
        setting_action.triggered.connect(self.open_settings)
        setting_menu.addAction(setting_action)

        # 트레이로 버튼
        tray_action = QAction('트레이로', self)
        tray_action.triggered.connect(self.minimize_to_tray)
        menubar.addAction(tray_action)

        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 주소 입력 영역
        connect_layout = QHBoxLayout()

        uid_label = QLabel('스트리머 UID')
        uid_label.setStyleSheet('color: #aaaaaa; padding: 0 5px;')
        connect_layout.addWidget(uid_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('예: 17aa057a8248b53affe30512a91481f5')
        self.url_input.setStyleSheet('''
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333;
                padding: 8px;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #00ff00;
            }
        ''')
        self.url_input.returnPressed.connect(self.on_connect_clicked)
        connect_layout.addWidget(self.url_input)

        self.connect_btn = QPushButton('연결')
        self.connect_btn.setStyleSheet('''
            QPushButton {
                background-color: #00ff00;
                color: #000000;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00cc00;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        ''')
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        connect_layout.addWidget(self.connect_btn)
        layout.addLayout(connect_layout)

        # 상태 표시
        self.status_label = QLabel('스트리머 주소를 입력하고 연결 버튼을 눌러주세요')
        self.status_label.setStyleSheet('color: gray; padding: 5px;')
        layout.addWidget(self.status_label)

        # 채팅 표시 영역
        chat_container = QWidget()
        chat_container_layout = QVBoxLayout(chat_container)
        chat_container_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_display = ClickableTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('맑은 고딕', self.settings.get('font_size', 10)))
        self.chat_display.setStyleSheet('''
            QTextEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333;
                padding: 10px;
            }
        ''')
        self.chat_display.user_clicked.connect(self.on_user_clicked)
        chat_container_layout.addWidget(self.chat_display)
        layout.addWidget(chat_container)

        # 최신 채팅 오버레이
        self.latest_chat_overlay = QLabel()
        self.latest_chat_overlay.setParent(self.chat_display)
        self.latest_chat_overlay.setWordWrap(True)
        self.latest_chat_overlay.setStyleSheet('''
            QLabel {
                background-color: rgba(26, 26, 26, 0.95);
                color: #aaaaaa;
                padding: 6px 10px;
                border-left: 3px solid #00ff00;
                font-size: 10px;
            }
        ''')
        self.latest_chat_overlay.hide()

        self.overlay_opacity = QGraphicsOpacityEffect(self.latest_chat_overlay)
        self.latest_chat_overlay.setGraphicsEffect(self.overlay_opacity)
        self.overlay_opacity.setOpacity(1.0)

        self.overlay_timer = QTimer()
        self.overlay_timer.setSingleShot(True)
        self.overlay_timer.timeout.connect(self.hide_overlay)

        # 스타일 설정
        self.setStyleSheet('''
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #cccccc;
            }
        ''')

    def init_tray_icon(self):
        """시스템 트레이 아이콘 초기화"""
        if not os.path.exists(ICON_PATH):
            return

        self.tray_icon = QSystemTrayIcon(QIcon(ICON_PATH), self)

        tray_menu = QMenu()
        show_action = QAction('열기', self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        quit_action = QAction('종료', self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_window(self):
        """창 표시"""
        self.show()
        self.activateWindow()

    def minimize_to_tray(self):
        """트레이로 최소화"""
        if hasattr(self, 'tray_icon'):
            self.hide()

    def quit_app(self):
        """앱 종료"""
        # 버퍼에 남은 채팅 전송
        self.send_batch_to_server()
        self.batch_timer.stop()

        if self.worker:
            self.worker.stop()
            self.worker.wait()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        QApplication.quit()

    def open_settings(self):
        """설정 다이얼로그 열기"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings = dialog.get_settings()
            self.save_settings()
            self.apply_settings()

    def apply_settings(self):
        """설정 적용"""
        font_size = self.settings.get('font_size', 10)
        self.chat_display.setFont(QFont('맑은 고딕', font_size))

    def setup_logger(self, channel_name):
        """채팅 로거 설정"""
        self.log_channel_name = channel_name
        self.current_log_date = None
        self._update_log_handler()
        self.chat_logger.info(f'\n=== 채팅 수집 시작: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===')

    def _update_log_handler(self):
        """현재 날짜에 맞는 로그 핸들러로 업데이트"""
        today = datetime.date.today()
        if self.current_log_date == today:
            return

        if self.chat_logger:
            for handler in self.chat_logger.handlers[:]:
                handler.close()
                self.chat_logger.removeHandler(handler)

        log_dir = os.path.join(LOG_DIR, self.log_channel_name)
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, f'{today.strftime("%Y-%m-%d")}.log')

        logger_name = f'chzzk_chat_{self.log_channel_name}'
        self.chat_logger = logging.getLogger(logger_name)
        self.chat_logger.setLevel(logging.INFO)
        self.chat_logger.handlers.clear()

        handler = logging.FileHandler(log_path, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.chat_logger.addHandler(handler)

        self.current_log_date = today

    def log_chat(self, time_str, chat_type, nickname, uid, message):
        """채팅 로그 기록"""
        if self.chat_logger:
            self._update_log_handler()
            self.chat_logger.info(f'[{time_str}][{chat_type}][{uid}] {nickname}: {message}')

    def add_to_batch_buffer(self, chat_data):
        """배치 전송 버퍼에 채팅 추가"""
        if not self.worker:
            return

        self.chat_buffer.append({
            'channel_id': self.streamer,
            'channel_name': getattr(self.worker, 'channelName', None),
            'user_id': chat_data['uid'],
            'nickname': chat_data['nickname'],
            'message': chat_data['message'],
            'message_type': 'donation' if chat_data['type'] == '후원' else 'chat',
            'chat_time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            # 추가 필드
            'subscription_month': chat_data.get('subscription_month'),
            'subscription_tier': chat_data.get('subscription_tier'),
            'os_type': chat_data.get('os_type'),
            'user_role': chat_data.get('user_role')
        })

        # 버퍼가 1000건 이상이면 즉시 전송
        if len(self.chat_buffer) >= 1000:
            self.send_batch_to_server()

    def send_batch_to_server(self):
        """버퍼의 채팅을 서버로 배치 전송"""
        if not self.chat_buffer:
            return

        batch_data = self.chat_buffer.copy()
        self.chat_buffer.clear()

        try:
            headers = {}
            if API_KEY:
                headers["Authorization"] = f"Bearer {API_KEY}"
            response = requests.post(
                f"{API_SERVER_URL}/chat/bulk",
                json=batch_data,
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                print(f"[배치 전송 완료] {result.get('saved', 0)}건 저장")
            else:
                print(f"[배치 전송 실패] 상태코드: {response.status_code}")
                self.chat_buffer.extend(batch_data)
        except Exception as e:
            print(f"[배치 전송 오류] {e}")
            # 오류 시 버퍼에 다시 추가 (최대 2000건까지)
            self.chat_buffer.extend(batch_data[:2000 - len(self.chat_buffer)])

    def on_tray_activated(self, reason):
        """트레이 아이콘 클릭 시"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def extract_streamer_id(self, url_or_id):
        """URL에서 스트리머 ID 추출"""
        url_or_id = url_or_id.strip()
        if 'chzzk.naver.com/' in url_or_id:
            parts = url_or_id.split('chzzk.naver.com/')
            if len(parts) > 1:
                channel_part = parts[1].split('/')[0].split('?')[0]
                return channel_part
        return url_or_id

    def on_connect_clicked(self):
        """연결/연결 해제 버튼 클릭 시"""
        if self.is_connected:
            self.disconnect_chat()
        else:
            self.connect_chat()

    def connect_chat(self):
        """채팅 연결"""
        url_or_id = self.url_input.text().strip()
        if not url_or_id:
            self.status_label.setText('스트리머 주소를 입력해주세요')
            self.status_label.setStyleSheet('color: #ff0000; padding: 5px;')
            return

        if self.worker:
            self.worker.stop()
            self.worker.wait()

        self.streamer = self.extract_streamer_id(url_or_id)
        self.connect_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.start_chat_worker()

    def disconnect_chat(self):
        """채팅 연결 해제"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.worker = None

        self.is_connected = False
        self.connect_btn.setText('연결')
        self.connect_btn.setStyleSheet('''
            QPushButton {
                background-color: #00ff00;
                color: #000000;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00cc00;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        ''')
        self.url_input.setEnabled(True)
        self.status_label.setText('연결이 해제되었습니다. 다른 스트리머에 연결할 수 있습니다.')
        self.status_label.setStyleSheet('color: gray; padding: 5px;')

    def start_chat_worker(self):
        """채팅 워커 스레드 시작"""
        self.worker = ChatWorker(self.streamer, self.cookies)
        self.worker.chat_received.connect(self.on_chat_received)
        self.worker.status_changed.connect(self.on_status_changed)
        self.worker.start()

    def on_chat_received(self, chat_data):
        """채팅 메시지 수신 시 호출"""
        time_str = chat_data['time']
        chat_type = chat_data['type']
        nickname = chat_data['nickname']
        message = chat_data['message']
        uid = chat_data['uid']
        color_code = chat_data.get('colorCode')
        badges = chat_data.get('badges', [])
        emojis = chat_data.get('emojis', {})

        # 사용자별 메시지 저장
        self.user_messages[uid].append({
            'time': time_str,
            'type': chat_type,
            'message': message
        })
        self.user_nicknames[uid] = nickname

        # 채팅 로그 기록 (로컬 파일)
        self.log_chat(time_str, chat_type, nickname, uid, message)

        # 서버 전송 버퍼에 추가
        self.add_to_batch_buffer(chat_data)

        # 닉네임 색상 결정
        if chat_type == '후원':
            color = '#ffcc00'
            prefix = '[후원] '
        else:
            color = self.get_user_color(uid, color_code)
            prefix = ''

        # 배지 HTML 생성
        badge_html = ''
        for badge_url in badges[:3]:
            badge_path = self.get_badge_path(badge_url)
            if badge_path:
                badge_html += f'<img src="file:///{badge_path.replace(os.sep, "/")}" width="18" height="18" style="vertical-align: middle;"/> '

        # 이모지 처리
        display_message = self.process_message_emojis(message, emojis)

        # HTML 형식으로 채팅 추가
        html = f'''<span style="color: #888888;">[{time_str}]</span>
        {badge_html}
        <a href="user:{uid}" style="color: {color}; text-decoration: none;">{prefix}<b>{nickname}</b></a>
        <span style="color: #ffffff;">{display_message}</span>'''
        # <span style="color: #666666;"> ({uid[:8]}...)</span>: # uid는 log에만 기록되면 될것같아.

        self.chat_display.append(html)

        # 스크롤이 맨 아래가 아닐 때만 오버레이 표시
        scrollbar = self.chat_display.verticalScrollBar()
        is_at_bottom = scrollbar.value() >= scrollbar.maximum() - 50

        if not is_at_bottom:
            self.show_latest_chat(f"{prefix}{nickname}: {message}")
        else:
            self.hide_overlay()

    def show_latest_chat(self, text):
        """하단 오버레이에 최신 채팅 표시"""
        display_text = text if len(text) <= 60 else text[:57] + '...'
        self.latest_chat_overlay.setText(f'↓ {display_text}')
        self.latest_chat_overlay.adjustSize()
        self.update_overlay_position()
        self.overlay_opacity.setOpacity(0.9)
        self.latest_chat_overlay.show()
        self.overlay_timer.start(5000)

    def update_overlay_position(self):
        """오버레이를 chat_display 하단 좌측에 배치"""
        overlay_height = self.latest_chat_overlay.sizeHint().height()
        overlay_width = min(self.latest_chat_overlay.sizeHint().width(), self.chat_display.width() - 20)
        parent_height = self.chat_display.height()

        self.latest_chat_overlay.setGeometry(
            5,
            parent_height - overlay_height - 5,
            overlay_width,
            overlay_height
        )

    def hide_overlay(self):
        """오버레이 숨김"""
        self.latest_chat_overlay.hide()

    def on_user_clicked(self, uid):
        """사용자 닉네임 클릭 시 팝업 표시"""
        if uid in self.user_nicknames:
            nickname = self.user_nicknames[uid]
            messages = self.user_messages[uid]
            dialog = UserChatDialog(uid, nickname, messages, self)
            # MainWindow 기준 상대 위치로 팝업 (우측에 표시)
            main_geo = self.geometry()
            dialog_x = main_geo.x() + main_geo.width() + 10
            dialog_y = main_geo.y()
            dialog.move(dialog_x, dialog_y)
            dialog.exec()

    def resizeEvent(self, event):
        """윈도우 크기 변경 시 오버레이 위치 업데이트"""
        super().resizeEvent(event)
        if hasattr(self, 'latest_chat_overlay'):
            self.update_overlay_position()

    def on_status_changed(self, status):
        """상태 변경 시 호출"""
        self.status_label.setText(status)
        if '완료' in status:
            self.status_label.setStyleSheet('color: #00ff00; padding: 5px;')
            self.is_connected = True
            self.connect_btn.setText('연결 해제')
            self.connect_btn.setStyleSheet('''
                QPushButton {
                    background-color: #ff6666;
                    color: #ffffff;
                    border: none;
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff4444;
                }
            ''')
            self.connect_btn.setEnabled(True)
            if self.worker and hasattr(self.worker, 'channelName'):
                self.setup_logger(self.worker.channelName)
        elif '실패' in status:
            self.status_label.setStyleSheet('color: #ff0000; padding: 5px;')
            self.is_connected = False
            self.connect_btn.setText('연결')
            self.connect_btn.setEnabled(True)
            self.url_input.setEnabled(True)
        else:
            self.status_label.setStyleSheet('color: #ffcc00; padding: 5px;')

    def closeEvent(self, event):
        """윈도우 X 버튼 클릭 시 앱 종료"""
        # 버퍼에 남은 채팅 전송
        self.send_batch_to_server()
        self.batch_timer.stop()

        # 창 크기 저장
        self.settings['window_width'] = self.width()
        self.settings['window_height'] = self.height()
        self.save_settings()

        if self.worker:
            self.worker.stop()
            self.worker.wait()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        event.accept()
