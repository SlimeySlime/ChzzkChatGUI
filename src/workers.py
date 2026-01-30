"""
WebSocket 채팅 수신 워커 스레드
"""
import json
import datetime

from PyQt6.QtCore import QThread, pyqtSignal
from websocket import WebSocket

import api
from cmd_type import CHZZK_CHAT_CMD


class ChatWorker(QThread):
    """WebSocket 채팅 수신을 담당하는 워커 스레드"""
    chat_received = pyqtSignal(dict)  # 채팅 메시지 시그널
    status_changed = pyqtSignal(str)  # 상태 변경 시그널

    def __init__(self, streamer, cookies):
        super().__init__()
        self.streamer = streamer
        self.cookies = cookies
        self.running = True
        self.sock = None
        self.sid = None
        self.chatChannelId = None
        self.channelName = None

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
                    self._process_chat_data(chat_data, chat_type)

            except Exception as e:
                if self.running:
                    try:
                        self.connect_chat()
                    except:
                        pass

    def _process_chat_data(self, chat_data, chat_type):
        """개별 채팅 데이터 처리"""
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
                    return
            except:
                return

        msg_time = datetime.datetime.fromtimestamp(chat_data['msgTime'] / 1000)
        msg_time_str = msg_time.strftime('%H:%M:%S')

        # 이모지 정보 추출
        emojis = {}
        try:
            if 'extras' in chat_data and chat_data['extras']:
                extras = json.loads(chat_data['extras'])
                emojis = extras.get('emojis', {})
        except:
            pass

        # 메인 스레드로 시그널 전송
        self.chat_received.emit({
            'time': msg_time_str,
            'type': chat_type,
            'uid': chat_data['uid'],
            'nickname': nickname,
            'message': chat_data['msg'],
            'colorCode': color_code,
            'badges': badges,
            'emojis': emojis
        })

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
