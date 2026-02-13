"""Step 2: URL 파싱 + API 호출 테스트"""

import sys
import os

# src/ 모듈 import 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import extract_streamer_id
import api


# ── URL 파싱 테스트 ──

def test_extract_direct_uid():
    uid = "17aa057a8248b53affe30512a91481f5"
    assert extract_streamer_id(uid) == uid


def test_extract_from_live_url():
    url = "https://chzzk.naver.com/live/17aa057a8248b53affe30512a91481f5"
    assert extract_streamer_id(url) == "17aa057a8248b53affe30512a91481f5"


def test_extract_from_channel_url():
    url = "https://chzzk.naver.com/17aa057a8248b53affe30512a91481f5"
    assert extract_streamer_id(url) == "17aa057a8248b53affe30512a91481f5"


def test_extract_from_chzzkban_url():
    url = "https://chzzkban.xyz/chzzk/channel/17aa057a8248b53affe30512a91481f5"
    assert extract_streamer_id(url) == "17aa057a8248b53affe30512a91481f5"


def test_extract_with_whitespace():
    assert extract_streamer_id("  17aa057a8248b53affe30512a91481f5  ") == "17aa057a8248b53affe30512a91481f5"


def test_extract_invalid_returns_original():
    assert extract_streamer_id("not-a-uid") == "not-a-uid"


def test_extract_empty():
    assert extract_streamer_id("") == ""


# ── API 호출 테스트 (실제 네트워크) ──

def test_fetch_channelName():
    """공개 API - 쿠키 불필요"""
    name = api.fetch_channelName("17aa057a8248b53affe30512a91481f5")
    assert isinstance(name, str)
    assert len(name) > 0
