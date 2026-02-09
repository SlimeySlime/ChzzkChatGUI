# Code from https://github.com/kimcore/chzzk/blob/main/src/chat/types.ts

CHZZK_CHAT_CMD = {
    'ping'                : 0,
    'pong'                : 10000,  
    'connect'             : 100,
    'send_chat'           : 3101,
    'request_recent_chat' : 5101,
    'chat'                : 93101,  # chat CMD code  
    'donation'            : 93102,  # donation CMD code
}

''' Chat Data example
= raw_message == self.sock.recv() 
{
    "svcid": "game",
    "ver": "1",
    "bdy": [
        {
            "svcid": "game",
            "cid": "N2G4yj",
            "mbrCnt": 2169,
            "uid": "0f0cc02bad11d7dabee2d55f6d0313f6",
            "profile": "{\"userIdHash\":\"0f0cc02bad11d7dabee2d55f6d0313f6\",\"nickname\":\"뮌스터\",\"profileImageUrl\":\"\",\"userRoleCode\":\"common_user\",\"badge\":null,\"title\":null,\"verifiedMark\":false,\"activityBadges\":[],\"streamingProperty\":{\"nicknameColor\":{\"colorCode\":\"CC000\"},\"activatedAchievementBadgeIds\":[]},\"viewerBadges\":[]}",
            "msg": "가오는",
            "msgTypeCode": 1,
            "msgStatusType": "NORMAL",
            "extras": "{\"osType\":\"AOS\",\"chatType\":\"STREAMING\",\"streamingChannelId\":\"17aa057a8248b53affe30512a91481f5\",\"emojis\":{},\"extraToken\":\"ynKmZPnUVyEEr1x0ddOPXY6yhFRrxY7rbhvxZ4Nflvbf1UICwPHjZKV+1rZYFI0sIKmMGNkw+lBS+Dmf8SIVnA==\"}",
            "ctime": 1769585095674,
            "utime": 1769585095674,
            "msgTid": null,
            "cuid": null,
            "msgTime": 1769585095674
        }
    ],
    "cmd": 93101,
    "tid": "3541-1769585096169-55",
    "cid": "N2G4yj"
}

'''