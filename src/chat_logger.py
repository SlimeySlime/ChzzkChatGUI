"""채팅 로그 기록

log/{channel_name}/YYYY-MM-DD.log 형식으로 날짜별 파일에 기록.
날짜가 바뀌면 자동으로 새 파일로 롤오버.
"""

import datetime
import logging
import os

from config import LOG_DIR


class ChatLogger:
    def __init__(self):
        self._logger = logging.getLogger('chzzk_chat_log')
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._handler = None
        self._current_date = None
        self._channel_name = None

    def setup(self, channel_name: str):
        """채널 로거 초기화. 연결 성공 시 호출."""
        self._channel_name = channel_name
        self._update_handler()

    def _update_handler(self):
        """날짜에 맞는 파일 핸들러 설정 (롤오버)"""
        today = datetime.date.today()
        if self._handler and self._current_date == today:
            return

        if self._handler:
            self._logger.removeHandler(self._handler)
            self._handler.close()

        channel_dir = os.path.join(LOG_DIR, self._channel_name)
        os.makedirs(channel_dir, exist_ok=True)

        log_path = os.path.join(channel_dir, f'{today.isoformat()}.log')
        self._handler = logging.FileHandler(log_path, encoding='utf-8')
        self._handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(self._handler)
        self._current_date = today

    def log(self, chat_data: dict):
        """채팅 한 건 기록"""
        if not self._channel_name:
            return

        self._update_handler()

        time_str = chat_data['time']
        chat_type = chat_data['type']
        uid = chat_data['uid']
        nickname = chat_data['nickname']
        message = chat_data['message']

        self._logger.info('[%s][%s][%s] %s: %s', time_str, chat_type, uid, nickname, message)

    def close(self):
        """핸들러 정리"""
        if self._handler:
            self._logger.removeHandler(self._handler)
            self._handler.close()
            self._handler = None
        self._channel_name = None
        self._current_date = None
