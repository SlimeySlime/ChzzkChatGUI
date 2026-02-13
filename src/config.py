"""경로 설정 및 상수 정의"""
import os


def _get_base_dir():
    """프로젝트 루트 디렉토리 (src/의 상위)"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _get_base_dir()

# 사용자 데이터 경로
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
BADGE_CACHE_DIR = os.path.join(CACHE_DIR, 'badges')
EMOJI_CACHE_DIR = os.path.join(CACHE_DIR, 'emojis')
LOG_DIR = os.path.join(BASE_DIR, 'log')
SETTINGS_PATH = os.path.join(BASE_DIR, 'settings.json')
COOKIES_PATH = os.path.join(BASE_DIR, 'cookies.json')
ENV_PATH = os.path.join(BASE_DIR, '.env')


def _load_env():
    """간단한 .env 파서 (KEY=VALUE 형식)"""
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env[key.strip()] = value.strip().strip('"').strip("'")
    return env


_env = _load_env()
BUG_REPORT_EMAIL = _env.get('BUG_REPORT_EMAIL', '')

# 디렉토리 생성
os.makedirs(BADGE_CACHE_DIR, exist_ok=True)
os.makedirs(EMOJI_CACHE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
