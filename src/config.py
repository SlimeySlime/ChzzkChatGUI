"""
경로 설정 및 상수 정의
PyInstaller 빌드 호환 처리 포함
"""
import os
import sys


def get_base_dir():
    """
    애플리케이션 기본 디렉토리 반환
    - 개발 환경: 스크립트 파일 위치
    - PyInstaller 빌드: 실행 파일 위치
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 경우
        return os.path.dirname(sys.executable)
    else:
        # 개발 환경
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_dir():
    """
    리소스 디렉토리 반환 (img, 기본 설정 등)
    - 개발 환경: 프로젝트 루트
    - PyInstaller --onedir: _internal 폴더
    - PyInstaller --onefile: 임시 폴더 (_MEIPASS)
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 빌드
        if hasattr(sys, '_MEIPASS'):
            # --onefile 모드: 임시 폴더에서 리소스 로드
            return sys._MEIPASS
        else:
            # --onedir 모드: _internal 폴더에 리소스가 있음
            exe_dir = os.path.dirname(sys.executable)
            internal_dir = os.path.join(exe_dir, '_internal')
            if os.path.exists(internal_dir):
                return internal_dir
            return exe_dir
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 기본 경로들
BASE_DIR = get_base_dir()
RESOURCE_DIR = get_resource_dir()

# 사용자 데이터 경로 (캐시, 로그, 설정 - 항상 실행 파일 위치 기준)
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
BADGE_CACHE_DIR = os.path.join(CACHE_DIR, 'badges')
EMOJI_CACHE_DIR = os.path.join(CACHE_DIR, 'emojis')
LOG_DIR = os.path.join(BASE_DIR, 'log')
SETTINGS_PATH = os.path.join(BASE_DIR, 'settings.json')
COOKIES_PATH = os.path.join(BASE_DIR, 'cookies.json')

# 리소스 경로 (이미지 등 - 번들에 포함된 리소스)
IMG_DIR = os.path.join(RESOURCE_DIR, 'img')
ICON_PATH = os.path.join(IMG_DIR, 'chzzk.png')

# API 서버 설정
API_SERVER_URL = "http://localhost:8000"

# 디렉토리 생성
os.makedirs(BADGE_CACHE_DIR, exist_ok=True)
os.makedirs(EMOJI_CACHE_DIR, exist_ok=True)
