"""Chzzk API 호출"""
import requests

HEADERS = {'User-Agent': ''}


def fetch_chatChannelId(streamer: str, cookies: dict) -> str:
    url = f'https://api.chzzk.naver.com/polling/v2/channels/{streamer}/live-status'
    response = requests.get(url, cookies=cookies, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    chat_channel_id = data['content']['chatChannelId']
    if chat_channel_id is None:
        raise ValueError('chatChannelId가 없습니다 (방송이 꺼져 있을 수 있음)')
    return chat_channel_id


def fetch_channelName(streamer: str) -> str:
    url = f'https://api.chzzk.naver.com/service/v1/channels/{streamer}'
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return data['content']['channelName']


def fetch_accessToken(chatChannelId: str, cookies: dict) -> tuple[str, str]:
    url = f'https://comm-api.game.naver.com/nng_main/v1/chats/access-token?channelId={chatChannelId}&chatType=STREAMING'
    response = requests.get(url, cookies=cookies, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return data['content']['accessToken'], data['content']['extraToken']


def fetch_userIdHash(cookies: dict) -> str:
    url = 'https://comm-api.game.naver.com/nng_main/v1/user/getUserStatus'
    response = requests.get(url, cookies=cookies, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return data['content']['userIdHash']
