import sys
import os
import json
import datetime
import argparse

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTextEdit, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor

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


class ChzzkChatUI(QMainWindow):
    """메인 UI 윈도우"""

    def __init__(self, streamer, cookies):
        super().__init__()
        self.streamer = streamer
        self.cookies = cookies
        self.init_ui()
        self.start_chat_worker()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle('Chzzk Chat')
        self.setGeometry(100, 100, 500, 600)

        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 상태 표시
        self.status_label = QLabel('연결 대기 중...')
        self.status_label.setStyleSheet('color: gray; padding: 5px;')
        layout.addWidget(self.status_label)

        # 채팅 표시 영역
        self.chat_display = QTextEdit()
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
        layout.addWidget(self.chat_display)

        # 스타일 설정
        self.setStyleSheet('''
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #cccccc;
            }
        ''')

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

        # 후원은 다른 색상으로 표시
        if chat_type == '후원':
            color = '#ffcc00'
            prefix = '[후원] '
        else:
            color = '#00ff00'
            prefix = ''

        # HTML 형식으로 채팅 추가
        html = f'''
        <span style="color: #888888;">[{time_str}]</span>
        <span style="color: {color};">{prefix}<b>{nickname}</b></span>
        <span style="color: #666666;"> ({uid[:8]}...)</span>:
        <span style="color: #ffffff;">{message}</span><br>
        '''

        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertHtml(html)

        # 자동 스크롤
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_status_changed(self, status):
        """상태 변경 시 호출"""
        self.status_label.setText(status)
        if '완료' in status:
            self.status_label.setStyleSheet('color: #00ff00; padding: 5px;')
        elif '실패' in status:
            self.status_label.setStyleSheet('color: #ff0000; padding: 5px;')
        else:
            self.status_label.setStyleSheet('color: #ffcc00; padding: 5px;')

    def closeEvent(self, event):
        """윈도우 종료 시 워커 정리"""
        self.worker.stop()
        self.worker.wait()
        event.accept()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--streamer_id', type=str, default='17aa057a8248b53affe30512a91481f5')
    args = parser.parse_args()

    cookies_path = os.path.join(SCRIPT_DIR, 'cookies.json')
    with open(cookies_path) as f:
        cookies = json.load(f)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = ChzzkChatUI(args.streamer_id, cookies)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
