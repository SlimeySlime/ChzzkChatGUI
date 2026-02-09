"""
채팅 로그 파일 기록
log/{channel_name}/YYYY-MM-DD.log 형식
"""
import os
import datetime
import logging

from config import LOG_DIR


class ChatLogger:
    """채널별/날짜별 채팅 로그 기록"""

    def __init__(self, channel_name):
        self.channel_name = channel_name
        self.current_log_date = None
        self._logger = None
        self._setup()

    def _setup(self):
        self._update_handler()
        self._logger.info(
            f'\n=== 채팅 수집 시작: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ==='
        )

    def _update_handler(self):
        """현재 날짜에 맞는 로그 핸들러로 업데이트"""
        today = datetime.date.today()
        if self.current_log_date == today:
            return

        if self._logger:
            for handler in self._logger.handlers[:]:
                handler.close()
                self._logger.removeHandler(handler)

        log_dir = os.path.join(LOG_DIR, self.channel_name)
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, f'{today.strftime("%Y-%m-%d")}.log')

        logger_name = f'chzzk_chat_{self.channel_name}'
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.INFO)
        self._logger.handlers.clear()

        handler = logging.FileHandler(log_path, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self._logger.addHandler(handler)

        self.current_log_date = today

    def log(self, time_str, chat_type, nickname, uid, message):
        """채팅 한 건 기록"""
        self._update_handler()
        self._logger.info(f'[{time_str}][{chat_type}][{uid}] {nickname}: {message}')
