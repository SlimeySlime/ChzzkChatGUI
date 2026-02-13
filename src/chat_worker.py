"""WebSocket 채팅 수신 워커 (async)

Flet은 async-first 프레임워크로, 백그라운드 스레드에서 page.update()를 호출하면
UI가 실시간 갱신되지 않는 문제가 있다 (Flet GitHub Issue #3571, #5902).

해결: ChatWorker를 async 클래스로 구현하고, page.run_task()로 Flet 이벤트 루프에서 실행.
이렇게 하면 콜백(on_chat, on_status)이 같은 이벤트 루프에서 호출되므로
page.update()가 안전하게 동작한다.

- websockets (async) 라이브러리 사용 (websocket-client 동기 라이브러리 대신)
- api.py의 동기 HTTP 호출은 asyncio.to_thread()로 감싸서 이벤트 루프 블록 방지
"""

import asyncio
import json
import datetime
import logging

import websockets

import api
from cmd_type import CHZZK_CHAT_CMD

logger = logging.getLogger(__name__)


class ChatWorker:
    """WebSocket 채팅 수신을 담당하는 비동기 워커

    사용법 (main.py에서):
        worker = ChatWorker(uid, cookies, on_chat, on_status)
        page.run_task(worker.run)  # Flet 이벤트 루프에서 실행
        await worker.stop()        # 중지
    """

    def __init__(self, streamer, cookies, on_chat_receive_callback, on_status_callback):
        self.streamer = streamer
        self.cookies = cookies
        self.on_chat_receive_callback = on_chat_receive_callback
        self.on_status_callback = on_status_callback
        self.running = True
        self.ws = None
        self.sid = None
        self.chatChannelId = None
        self.channelName = None

    async def connect_chat(self):
        """채팅 서버에 연결

        API 호출(requests 동기)은 asyncio.to_thread()로 감싸서
        이벤트 루프를 블록하지 않도록 한다.
        """
        self.userIdHash = await asyncio.to_thread(api.fetch_userIdHash, self.cookies)
        self.chatChannelId = await asyncio.to_thread(api.fetch_chatChannelId, self.streamer, self.cookies)
        self.channelName = await asyncio.to_thread(api.fetch_channelName, self.streamer)
        self.accessToken, self.extraToken = await asyncio.to_thread(api.fetch_accessToken, self.chatChannelId, self.cookies)

        self.on_status_callback(f'{self.channelName} 채팅창에 연결 중...')

        self.ws = await websockets.connect('wss://kr-ss1.chat.naver.com/chat')

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

        await self.ws.send(json.dumps(dict(send_dict, **default_dict)))
        sock_response = json.loads(await self.ws.recv())
        self.sid = sock_response['bdy']['sid']

        send_dict = {
            "cmd": CHZZK_CHAT_CMD['request_recent_chat'],
            "tid": 2,
            "sid": self.sid,
            "bdy": {
                "recentMessageCount": 50
            }
        }

        await self.ws.send(json.dumps(dict(send_dict, **default_dict)))
        await self.ws.recv()

        self.on_status_callback(f'{self.channelName} 채팅창 연결 완료')

    async def run(self):
        """메인 루프 — page.run_task()로 실행됨 (Flet 이벤트 루프 내)"""
        try:
            await self.connect_chat()
        except Exception as e:
            self.on_status_callback(f'연결 실패: {str(e)}')
            return

        while self.running:
            try:
                raw_message = await self.ws.recv()
                raw_message = json.loads(raw_message)
                chat_cmd = raw_message['cmd']

                if chat_cmd == CHZZK_CHAT_CMD['ping']:
                    await self.ws.send(json.dumps({
                        "ver": "2",
                        "cmd": CHZZK_CHAT_CMD['pong']
                    }))

                    new_channel_id = await asyncio.to_thread(
                        api.fetch_chatChannelId, self.streamer, self.cookies
                    )
                    if self.chatChannelId != new_channel_id:
                        await self.connect_chat()
                    continue

                if chat_cmd == CHZZK_CHAT_CMD['chat']:
                    chat_type = '채팅'
                elif chat_cmd == CHZZK_CHAT_CMD['donation']:
                    chat_type = '후원'
                else:
                    continue

                for chat_data in raw_message['bdy']:
                    self._process_chat_data(chat_data, chat_type)

            except websockets.ConnectionClosed:
                if self.running:
                    try:
                        await self.connect_chat()
                    except Exception:
                        logger.warning('재연결 실패', exc_info=True)
                        self.on_status_callback('재연결 실패')
                        break
            except Exception:
                if self.running:
                    try:
                        await self.connect_chat()
                    except Exception:
                        logger.warning('재연결 실패', exc_info=True)
                        self.on_status_callback('재연결 실패')
                        break

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

                streaming_prop = profile_data.get('streamingProperty', {})
                nickname_color = streaming_prop.get('nicknameColor', {})
                color_code = nickname_color.get('colorCode')

                subscription = streaming_prop.get('subscription', {})
                subscription_month = subscription.get('accumulativeMonth')
                subscription_tier = subscription.get('tier')

                sub_badge = subscription.get('badge', {})
                if sub_badge.get('imageUrl'):
                    badges.append(sub_badge['imageUrl'])

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

        emojis = {}
        os_type = None
        try:
            if 'extras' in chat_data and chat_data['extras']:
                extras = json.loads(chat_data['extras'])
                emojis = extras.get('emojis', {})
                os_type = extras.get('osType')
        except Exception:
            logger.debug('extras 파싱 실패', exc_info=True)

        self.on_chat_receive_callback({
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
            'user_role': user_role,
        })

    async def stop(self):
        self.running = False
        if self.ws:
            await self.ws.close()
