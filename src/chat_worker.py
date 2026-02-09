"""
WebSocket 채팅 수신 워커 (threading.Thread 기반)
PyQt6 의존성 없음 — 콜백 함수로 결과 전달
"""
import json
import datetime
import logging
import threading

from websockets.sync.client import connect as ws_connect

from api import (
    fetch_userIdHash, fetch_chatChannelId,
    fetch_channelName, fetch_accessToken
)
from cmd_type import CHZZK_CHAT_CMD

logger = logging.getLogger(__name__)


class ChatWorker(threading.Thread):
    """WebSocket 채팅 수신을 담당하는 워커 스레드"""

    def __init__(self, streamer, cookies, *,
                 on_chat_received=None, on_status_changed=None):
        super().__init__(daemon=True)
        self.streamer = streamer
        self.cookies = cookies
        self.on_chat_received = on_chat_received
        self.on_status_changed = on_status_changed
        self.running = True
        self.ws = None
        self.sid = None
        self.chatChannelId = None
        self.channelName = None

    def _emit_status(self, msg):
        if self.on_status_changed:
            self.on_status_changed(msg)

    def _emit_chat(self, data):
        if self.on_chat_received:
            self.on_chat_received(data)

    def connect_chat(self):
        """채팅 서버에 연결"""
        self.userIdHash = fetch_userIdHash(self.cookies)
        self.chatChannelId = fetch_chatChannelId(self.streamer, self.cookies)
        self.channelName = fetch_channelName(self.streamer)
        self.accessToken, self.extraToken = fetch_accessToken(
            self.chatChannelId, self.cookies
        )

        self._emit_status(f'{self.channelName} 채팅창에 연결 중...')

        # 기존 연결 정리
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

        self.ws = ws_connect('wss://kr-ss1.chat.naver.com/chat')

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

        self.ws.send(json.dumps(dict(send_dict, **default_dict)))
        sock_response = json.loads(self.ws.recv())
        self.sid = sock_response['bdy']['sid']

        send_dict = {
            "cmd": CHZZK_CHAT_CMD['request_recent_chat'],
            "tid": 2,
            "sid": self.sid,
            "bdy": {
                "recentMessageCount": 50
            }
        }

        self.ws.send(json.dumps(dict(send_dict, **default_dict)))
        self.ws.recv()

        self._emit_status(f'{self.channelName} 채팅창 연결 완료')

    def run(self):
        """메인 루프"""
        try:
            self.connect_chat()
        except Exception as e:
            self._emit_status(f'연결 실패: {str(e)}')
            return

        while self.running:
            try:
                raw_message = self.ws.recv()
                raw_message = json.loads(raw_message)
                chat_cmd = raw_message['cmd']

                if chat_cmd == CHZZK_CHAT_CMD['ping']:
                    self.ws.send(json.dumps({
                        "ver": "2",
                        "cmd": CHZZK_CHAT_CMD['pong']
                    }))

                    if self.chatChannelId != fetch_chatChannelId(
                        self.streamer, self.cookies
                    ):
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

            except Exception:
                if self.running:
                    try:
                        self.connect_chat()
                    except Exception:
                        logger.warning('재연결 실패', exc_info=True)

    def _process_chat_data(self, chat_data, chat_type):
        """개별 채팅 데이터 처리"""
        color_code = None
        badges = []
        subscription_month = None
        subscription_tier = None
        user_role = None

        if chat_data['uid'] == 'anonymous':
            nickname = '익명의 후원자'
        else:
            try:
                profile_data = json.loads(chat_data['profile'])
                nickname = profile_data["nickname"]
                user_role = profile_data.get('userRoleCode')

                # colorCode 추출
                streaming_prop = profile_data.get('streamingProperty', {})
                nickname_color = streaming_prop.get('nicknameColor', {})
                color_code = nickname_color.get('colorCode')

                # 구독 정보 추출
                subscription = streaming_prop.get('subscription', {})
                subscription_month = subscription.get('accumulativeMonth')
                subscription_tier = subscription.get('tier')

                # 배지 추출 — 구독 배지
                sub_badge = subscription.get('badge', {})
                if sub_badge.get('imageUrl'):
                    badges.append(sub_badge['imageUrl'])

                # 활동 배지
                for badge in profile_data.get('activityBadges', []):
                    if badge.get('imageUrl') and badge.get('activated'):
                        badges.append(badge['imageUrl'])

                if 'msg' not in chat_data:
                    return
            except Exception:
                logger.debug('프로필 파싱 실패: uid=%s', chat_data.get('uid'), exc_info=True)
                return

        msg_time = datetime.datetime.fromtimestamp(chat_data['msgTime'] / 1000)
        msg_time_str = msg_time.strftime('%H:%M:%S')

        # 이모지, OS 타입 추출
        emojis = {}
        os_type = None
        try:
            if 'extras' in chat_data and chat_data['extras']:
                extras = json.loads(chat_data['extras'])
                emojis = extras.get('emojis', {})
                os_type = extras.get('osType')
        except Exception:
            logger.debug('extras 파싱 실패', exc_info=True)

        self._emit_chat({
            'time': msg_time_str,
            'type': chat_type,
            'uid': chat_data['uid'],
            'nickname': nickname,
            'message': chat_data['msg'],
            'colorCode': color_code,
            'badges': badges,
            'emojis': emojis,
            'subscription_month': subscription_month,
            'subscription_tier': subscription_tier,
            'os_type': os_type,
            'user_role': user_role
        })

    def stop(self):
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
