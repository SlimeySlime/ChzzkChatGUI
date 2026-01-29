import sys
import os
import json
import datetime

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
                    if chat_data['uid'] == 'anonymous':
                        nickname = '익명의 후원자'
                    else:
                        try:
                            profile_data = json.loads(chat_data['profile'])
                            nickname = profile_data["nickname"]
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
                        'message': chat_data['msg']
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

    def __init__(self, cookies):
        super().__init__()
        self.streamer = None
        self.cookies = cookies
        self.worker = None
        self.is_connected = False
        self.user_messages = defaultdict(list)  # uid -> [messages]
        self.user_nicknames = {}  # uid -> nickname
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

        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 주소 입력 영역
        connect_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('스트리머 ID 또는 치지직 채널 URL 입력')
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

    def quit_app(self):
        """앱 종료"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        QApplication.quit()

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

        # 사용자별 메시지 저장
        self.user_messages[uid].append({
            'time': time_str,
            'type': chat_type,
            'message': message
        })
        self.user_nicknames[uid] = nickname

        # 후원은 다른 색상으로 표시
        if chat_type == '후원':
            color = '#ffcc00'
            prefix = '[후원] '
        else:
            color = '#00ff00'
            prefix = ''

        # HTML 형식으로 채팅 추가 (닉네임 클릭 가능)
        html = f'''<span style="color: #888888;">[{time_str}]</span>
        <a href="user:{uid}" style="color: {color}; text-decoration: none;">{prefix}<b>{nickname}</b></a>
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
        elif '실패' in status:
            self.status_label.setStyleSheet('color: #ff0000; padding: 5px;')
            self.is_connected = False
            self.connect_btn.setText('연결')
            self.connect_btn.setEnabled(True)
            self.url_input.setEnabled(True)
        else:
            self.status_label.setStyleSheet('color: #ffcc00; padding: 5px;')

    def closeEvent(self, event):
        """윈도우 X 버튼 클릭 시 트레이로 최소화"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            # show message 기능은 없앨거임
            # self.tray_icon.showMessage(
            #     'Chzzk Chat',
            #     '트레이에서 실행 중입니다. 종료하려면 트레이 아이콘을 우클릭하세요.',
            #     QSystemTrayIcon.MessageIcon.Information,
            #     2000
            # )
        else:
            # 트레이 아이콘이 없으면 앱 종료
            if self.worker:
                self.worker.stop()
                self.worker.wait()
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
