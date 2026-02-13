"""Step 3: ChatWorker 메시지 파싱 테스트"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chat_worker import ChatWorker


def make_chat_data(uid='user123', nickname='테스터', msg='안녕하세요',
                   msg_time=1700000000000, extras=None, profile_extras=None):
    """테스트용 raw chat_data 생성"""
    profile = {
        'nickname': nickname,
        'userRoleCode': 'common_user',
        'streamingProperty': {
            'nicknameColor': {'colorCode': 'CC000'},
            'subscription': {},
        },
        'activityBadges': [],
    }
    if profile_extras:
        profile.update(profile_extras)

    data = {
        'uid': uid,
        'profile': json.dumps(profile),
        'msg': msg,
        'msgTime': msg_time,
    }
    if extras is not None:
        data['extras'] = json.dumps(extras)
    return data


class TestProcessChatData:
    """_process_chat_data 단위 테스트 (WS 연결 없이)"""

    def setup_method(self):
        self.received = []
        self.worker = ChatWorker.__new__(ChatWorker)
        self.worker.on_chat_receive_callback = lambda data: self.received.append(data)
        self.worker.on_status_callback = lambda msg: None

    def test_basic_chat(self):
        raw = make_chat_data(msg='테스트 메시지')
        self.worker._process_chat_data(raw, '채팅')

        assert len(self.received) == 1
        result = self.received[0]
        assert result['nickname'] == '테스터'
        assert result['message'] == '테스트 메시지'
        assert result['type'] == '채팅'
        assert result['uid'] == 'user123'

    def test_anonymous_donor(self):
        raw = {
            'uid': 'anonymous',
            'msg': '후원합니다',
            'msgTime': 1700000000000,
        }
        self.worker._process_chat_data(raw, '후원')

        assert len(self.received) == 1
        assert self.received[0]['nickname'] == '익명의 후원자'
        assert self.received[0]['type'] == '후원'

    def test_color_code(self):
        raw = make_chat_data()
        self.worker._process_chat_data(raw, '채팅')
        assert self.received[0]['colorCode'] == 'CC000'

    def test_subscription_badge(self):
        profile_extras = {
            'streamingProperty': {
                'nicknameColor': {},
                'subscription': {
                    'accumulativeMonth': 12,
                    'tier': 1,
                    'badge': {'imageUrl': 'https://badge.example.com/sub.png'},
                },
            },
        }
        raw = make_chat_data(profile_extras=profile_extras)
        self.worker._process_chat_data(raw, '채팅')

        result = self.received[0]
        assert result['subscription_month'] == 12
        assert result['subscription_tier'] == 1
        assert 'https://badge.example.com/sub.png' in result['badges']

    def test_activity_badges(self):
        profile_extras = {
            'activityBadges': [
                {'imageUrl': 'https://badge1.png', 'activated': True},
                {'imageUrl': 'https://badge2.png', 'activated': False},
                {'imageUrl': 'https://badge3.png', 'activated': True},
            ],
        }
        raw = make_chat_data(profile_extras=profile_extras)
        self.worker._process_chat_data(raw, '채팅')

        badges = self.received[0]['badges']
        assert 'https://badge1.png' in badges
        assert 'https://badge2.png' not in badges
        assert 'https://badge3.png' in badges

    def test_emojis(self):
        raw = make_chat_data(extras={'emojis': {'smile': 'https://emoji.png'}, 'osType': 'PC'})
        self.worker._process_chat_data(raw, '채팅')

        result = self.received[0]
        assert result['emojis'] == {'smile': 'https://emoji.png'}
        assert result['os_type'] == 'PC'

    def test_time_format(self):
        # 2023-11-14 18:13:20 KST (UTC+9)
        raw = make_chat_data(msg_time=1700000000000)
        self.worker._process_chat_data(raw, '채팅')
        # 시간 형식만 확인 (타임존에 따라 값이 달라짐)
        assert len(self.received[0]['time']) == 8  # HH:MM:SS
        assert self.received[0]['time'].count(':') == 2

    def test_missing_msg_skipped(self):
        """msg 필드 없으면 스킵"""
        raw = make_chat_data()
        del raw['msg']
        self.worker._process_chat_data(raw, '채팅')
        assert len(self.received) == 0

    def test_malformed_profile_skipped(self):
        """프로필 파싱 실패 시 스킵"""
        raw = {
            'uid': 'user123',
            'profile': 'not-valid-json',
            'msg': '메시지',
            'msgTime': 1700000000000,
        }
        self.worker._process_chat_data(raw, '채팅')
        assert len(self.received) == 0


class TestChatWorkerLifecycle:
    """ChatWorker 생성/중지 테스트 (실제 WS 연결 없이)"""

    def test_create_and_stop(self):
        worker = ChatWorker('test_uid', {}, lambda d: None, lambda m: None)
        assert worker.daemon is True
        assert worker.running is True

        worker.stop()
        assert worker.running is False
