import sys
import os
import json
import datetime
import logging
import hashlib
import requests
from logging.handlers import TimedRotatingFileHandler

from collections import defaultdict
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QDialog, QScrollArea, QGraphicsOpacityEffect,
    QLineEdit, QPushButton, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt, QPropertyAnimation, QUrl
from PyQt6.QtGui import QFont, QDesktopServices, QIcon, QAction

# 스크립트 디렉토리 기준으로 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from websocket import WebSocket
import api
from cmd_type import CHZZK_CHAT_CMD     # no use now


class ChatWorker(QThread):
    """WebSocket 채팅 수신을 담당하는 워커 스레드"""
    chat_received = pyqtSignal(dict)  # 채팅 메시지 시그널
    status_changed = pyqtSignal(str)  # 상태 변경 시그널
    '''
        ChatWorker의 Signal.emit() -> ChzzkChatUI 메인스레드에서 recieved
    '''
    
    def __init__(self, streamer, cookies):
        super().__init__()
        self.streamer = streamer
        self.cookies = cookies
        self.running = True
        self.sock = None
        self.sid = None
        self.chatChannelId = None

    def connect_chat(self):
        """채팅 서버에 연결"""
        self.userIdHash = api.fetch_userIdHash(self.cookies)
        self.chatChannelId = api.fetch_chatChannelId(self.streamer, self.cookies)
        self.channelName = api.fetch_channelName(self.streamer)
        self.accessToken, self.extraToken = api.fetch_accessToken(self.chatChannelId, self.cookies)

        self.status_changed.emit(f'{self.channelName} 채팅창에 연결 중...')

        self.sock = WebSocket()
        self.sock.connect('wss://kr-ss1.chat.naver.com/chat')

        default_dict = {
            "ver": "2",
            "svcid": "game",
            "cid": self.chatChannelId,
        }

        send_dict = {
            "cmd": CHZZK_CHAT_CMD['connect'],
            "tid": 1,
            "bdy": {
                "uid": self.userIdHash,
                "devType": 2001,
                "accTkn": self.accessToken,
                "auth": "SEND"
            }
        }

        self.sock.send(json.dumps(dict(send_dict, **default_dict)))
        sock_response = json.loads(self.sock.recv())
        self.sid = sock_response['bdy']['sid']

        send_dict = {
            "cmd": CHZZK_CHAT_CMD['request_recent_chat'],
            "tid": 2,
            "sid": self.sid,
            "bdy": {
                "recentMessageCount": 50
            }
        }

        self.sock.send(json.dumps(dict(send_dict, **default_dict)))
        self.sock.recv()

        self.status_changed.emit(f'{self.channelName} 채팅창 연결 완료')

    def run(self):
        """메인 루프"""
        try:
            self.connect_chat()
        except Exception as e:
            self.status_changed.emit(f'연결 실패: {str(e)}')
            return

        while self.running:
            try:
                raw_message = self.sock.recv()
                raw_message = json.loads(raw_message)
                chat_cmd = raw_message['cmd']

                if chat_cmd == CHZZK_CHAT_CMD['ping']:
                    self.sock.send(json.dumps({
                        "ver": "2",
                        "cmd": CHZZK_CHAT_CMD['pong']
                    }))

                    if self.chatChannelId != api.fetch_chatChannelId(self.streamer, self.cookies):
                        self.connect_chat()
                    continue

                if chat_cmd == CHZZK_CHAT_CMD['chat']:
                    chat_type = '채팅'
                elif chat_cmd == CHZZK_CHAT_CMD['donation']:
                    chat_type = '후원'
                else:
                    continue

                for chat_data in raw_message['bdy']:
                    color_code = None
                    badges = []
                    if chat_data['uid'] == 'anonymous':
                        nickname = '익명의 후원자'
                    else:
                        try:
                            profile_data = json.loads(chat_data['profile'])
                            nickname = profile_data["nickname"]
                            # colorCode 추출
                            streaming_prop = profile_data.get('streamingProperty', {})
                            nickname_color = streaming_prop.get('nicknameColor', {})
                            color_code = nickname_color.get('colorCode')

                            # 배지 추출
                            # 1. 구독 배지
                            subscription = streaming_prop.get('subscription', {})
                            sub_badge = subscription.get('badge', {})
                            if sub_badge.get('imageUrl'):
                                badges.append(sub_badge['imageUrl'])

                            # 2. 활동 배지
                            for badge in profile_data.get('activityBadges', []):
                                if badge.get('imageUrl') and badge.get('activated'):
                                    badges.append(badge['imageUrl'])

                            if 'msg' not in chat_data:
                                continue
                        except:
                            continue

                    msg_time = datetime.datetime.fromtimestamp(chat_data['msgTime']/1000)
                    msg_time_str = msg_time.strftime('%H:%M:%S')

                    # necessary emit info to main thread
                    self.chat_received.emit({
                        'time': msg_time_str,
                        'type': chat_type,
                        'uid': chat_data['uid'],
                        'nickname': nickname,
                        'message': chat_data['msg'],
                        'colorCode': color_code,
                        'badges': badges
                    })

            except Exception as e:
                if self.running:
                    try:
                        self.connect_chat()
                    except:
                        pass

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()


class UserChatDialog(QDialog):
    """특정 사용자의 채팅 기록을 보여주는 팝업"""

    def __init__(self, uid, nickname, messages, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.nickname = nickname
        self.messages = messages
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'{self.nickname}의 채팅 기록')
        self.setGeometry(200, 200, 450, 400)
        self.setStyleSheet('''
            QDialog {
                background-color: #2b2b2b;
            }
        ''')

        layout = QVBoxLayout(self)

        # 사용자 정보 헤더
        header = QLabel(f'''
            <div style="padding: 10px;">
                <span style="color: #00ff00; font-size: 16px; font-weight: bold;">{self.nickname}</span><br>
                <span style="color: #666666; font-size: 11px;">UID: {self.uid}</span><br>
                <span style="color: #888888; font-size: 12px;">총 {len(self.messages)}개의 메시지</span>
            </div>
        ''')
        header.setStyleSheet('background-color: #1f1f1f; border-radius: 5px;')
        layout.addWidget(header)

        # 채팅 기록 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet('''
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
        ''')

        chat_widget = QWidget()
        chat_widget.setStyleSheet('background-color: #1a1a1a;')
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setSpacing(2)

        for msg in self.messages:
            msg_label = QLabel(f'''
                <span style="color: #888888;">[{msg['time']}]</span>
                <span style="color: {'#ffcc00' if msg['type'] == '후원' else '#ffffff'};">{msg['message']}</span>
            ''')
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet('padding: 5px; background-color: #252525; border-radius: 3px;')
            chat_layout.addWidget(msg_label)

        chat_layout.addStretch()
        scroll_area.setWidget(chat_widget)
        layout.addWidget(scroll_area)


class ClickableTextEdit(QTextEdit):
    """클릭 가능한 채팅 영역"""
    user_clicked = pyqtSignal(str)  # uid 전달

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            anchor = self.anchorAt(event.pos())
            if anchor and anchor.startswith('user:'):
                uid = anchor.replace('user:', '')
                self.user_clicked.emit(uid)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        anchor = self.anchorAt(event.pos())
        if anchor and anchor.startswith('user:'):
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)


class ChzzkChatUI(QMainWindow):
    """메인 UI 윈도우"""

    # 치지직 colorCode 매핑 테이블 (치트키 사용자용)
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

    # 일반 유저(CC000)용 색상 팔레트
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

    def get_user_color(self, uid, color_code):
        """uid와 colorCode 기반으로 닉네임 색상 반환"""
        # 치트키 색상(SG0~)이 있으면 해당 색상 사용
        if color_code and color_code in self.COLOR_CODE_MAP:
            return self.COLOR_CODE_MAP[color_code]
        # CC000이거나 없으면 uid 해시 기반 팔레트 색상
        hash_value = hash(uid)
        color_index = abs(hash_value) % len(self.USER_COLOR_PALETTE)
        return self.USER_COLOR_PALETTE[color_index]

    def get_badge_path(self, url):
        """배지 이미지 URL을 로컬 캐시 경로로 변환 (필요시 다운로드)"""
        if not url:
            return None

        # 캐시에 있으면 바로 반환
        if url in self.badge_cache:
            return self.badge_cache[url]

        try:
            # URL 해시로 파일명 생성
            url_hash = hashlib.md5(url.encode()).hexdigest()
            ext = os.path.splitext(url)[1] or '.png'
            local_path = os.path.join(self.badge_cache_dir, f'{url_hash}{ext}')

            # 이미 다운로드되어 있으면 캐시에 등록
            if os.path.exists(local_path):
                self.badge_cache[url] = local_path
                return local_path

            # 다운로드
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                self.badge_cache[url] = local_path
                return local_path
        except:
            pass

        return None

    def __init__(self, cookies):
        super().__init__()
        self.streamer = None
        self.cookies = cookies
        self.worker = None
        self.is_connected = False
        self.user_messages = defaultdict(list)  # uid -> [messages]
        self.user_nicknames = {}  # uid -> nickname
        self.chat_logger = None  # 채팅 로거
        self.badge_cache = {}  # 배지 이미지 캐시 (url -> local_path)
        self.badge_cache_dir = os.path.join(SCRIPT_DIR, 'cache', 'badges')
        os.makedirs(self.badge_cache_dir, exist_ok=True)
        self.init_ui()
        self.init_tray_icon()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle('Chzzk Chat')
        self.setGeometry(100, 100, 500, 600)

        # 아이콘 설정
        icon_path = os.path.join(SCRIPT_DIR, 'img', 'chzzk.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

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

        # 설정 메뉴 (placeholder)
        setting_menu = menubar.addMenu('설정')
        setting_placeholder = QAction('설정 (준비 중)', self)
        setting_placeholder.setEnabled(False)
        setting_menu.addAction(setting_placeholder)

        # 트레이로 버튼 (메뉴바에 직접 배치)
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

        # 채팅 표시 영역 (컨테이너로 감싸서 오버레이 배치)
        chat_container = QWidget()
        chat_container_layout = QVBoxLayout(chat_container)
        chat_container_layout.setContentsMargins(0, 0, 0, 0)

        # 유저 chat은 ClickableTextEdit 사용
        self.chat_display = ClickableTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('맑은 고딕', 10))
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

        # 최신 채팅 오버레이 (하단에 hover 스타일로 표시)
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

        # 오버레이 fade 효과
        self.overlay_opacity = QGraphicsOpacityEffect(self.latest_chat_overlay)
        self.latest_chat_overlay.setGraphicsEffect(self.overlay_opacity)
        self.overlay_opacity.setOpacity(1.0)

        # 오버레이 자동 숨김 타이머
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
        icon_path = os.path.join(SCRIPT_DIR, 'img', 'chzzk.png')
        if not os.path.exists(icon_path):
            return

        self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)

        # 트레이 메뉴
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
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        QApplication.quit()

    def setup_logger(self, channel_name):
        """채팅 로거 설정 (날짜별 자동 로테이션)"""
        # 기존 로거 정리
        if self.chat_logger:
            for handler in self.chat_logger.handlers[:]:
                handler.close()
                self.chat_logger.removeHandler(handler)

        # log/{channel_name}/ 디렉토리 생성
        log_dir = os.path.join(SCRIPT_DIR, 'log', channel_name)
        os.makedirs(log_dir, exist_ok=True)

        # 로거 생성
        logger_name = f'chzzk_chat_{channel_name}'
        self.chat_logger = logging.getLogger(logger_name)
        self.chat_logger.setLevel(logging.INFO)
        self.chat_logger.handlers.clear()

        # 날짜별 로테이션 핸들러 (자정에 새 파일 생성)
        log_path = os.path.join(log_dir, 'chat.log')
        handler = TimedRotatingFileHandler(
            log_path,
            when='midnight',
            interval=1,
            backupCount=30,  # 30일치 보관
            encoding='utf-8'
        )
        handler.suffix = '%Y-%m-%d.log'
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.chat_logger.addHandler(handler)

        # 시작 로그
        self.chat_logger.info(f'\n=== 채팅 수집 시작: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===')

    def log_chat(self, time_str, chat_type, nickname, uid, message):
        """채팅 로그 기록"""
        if self.chat_logger:
            self.chat_logger.info(f'[{time_str}][{chat_type}][{uid}] {nickname}: {message}')

    def on_tray_activated(self, reason):
        """트레이 아이콘 클릭 시"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def extract_streamer_id(self, url_or_id):
        """URL에서 스트리머 ID 추출"""
        url_or_id = url_or_id.strip()
        # chzzk.naver.com/채널ID 형태의 URL 처리
        if 'chzzk.naver.com/' in url_or_id:
            # URL에서 채널 ID 부분 추출
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

        # 기존 워커가 있으면 정리
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
        """채팅 워커 스레드 시작
            Worker 생성 - Signal 연결 - start()
        """
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

        # 사용자별 메시지 저장
        self.user_messages[uid].append({
            'time': time_str,
            'type': chat_type,
            'message': message
        })
        self.user_nicknames[uid] = nickname

        # 채팅 로그 기록
        self.log_chat(time_str, chat_type, nickname, uid, message)

        # 닉네임 색상 결정
        if chat_type == '후원':
            color = '#ffcc00'
            prefix = '[후원] '
        else:
            color = self.get_user_color(uid, color_code)
            prefix = ''

        # 배지 HTML 생성
        badge_html = ''
        for badge_url in badges[:3]:  # 최대 3개 배지만 표시
            badge_path = self.get_badge_path(badge_url)
            if badge_path:
                badge_html += f'<img src="file:///{badge_path.replace(os.sep, "/")}" width="18" height="18" style="vertical-align: middle;"/> '

        # HTML 형식으로 채팅 추가 (닉네임 클릭 가능)
        html = f'''<span style="color: #888888;">[{time_str}]</span>
        {badge_html}<a href="user:{uid}" style="color: {color}; text-decoration: none;">{prefix}<b>{nickname}</b></a>
        <span style="color: #666666;"> ({uid[:8]}...)</span>:
        <span style="color: #ffffff;">{message}</span>'''

        self.chat_display.append(html)

        # 스크롤이 맨 아래가 아닐 때만 오버레이 표시
        scrollbar = self.chat_display.verticalScrollBar()
        is_at_bottom = scrollbar.value() >= scrollbar.maximum() - 50

        if not is_at_bottom:
            self.show_latest_chat(f"{prefix}{nickname}: {message}")
        else:
            self.hide_overlay()

    def show_latest_chat(self, text):
        """하단 오버레이에 최신 채팅 표시 (hover 스타일)"""
        # 텍스트 길이 제한
        display_text = text if len(text) <= 60 else text[:57] + '...'
        self.latest_chat_overlay.setText(f'↓ {display_text}')
        self.latest_chat_overlay.adjustSize()
        self.update_overlay_position()
        self.overlay_opacity.setOpacity(0.9)
        self.latest_chat_overlay.show()
        # 5초 후 자동 숨김
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
            # 채팅 로그 시작
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
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        event.accept()


def main():
    cookies_path = os.path.join(SCRIPT_DIR, 'cookies.json')
    with open(cookies_path) as f:
        cookies = json.load(f)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 앱 전체 아이콘 설정
    icon_path = os.path.join(SCRIPT_DIR, 'img', 'chzzk.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = ChzzkChatUI(cookies)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
