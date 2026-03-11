import React, { memo } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { ChatData, getUserColor } from "../types/chat";

interface ChatItemProps {
  chat: ChatData;
  showTimestamp: boolean;
  showBadges: boolean;
  onNicknameClick?: (uid: string, nickname: string) => void;
}

/// 로컬 절대경로이면 asset:// URL로 변환, 네트워크 URL이면 그대로 반환
function toDisplaySrc(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("/") || /^[A-Za-z]:\\/.test(pathOrUrl)) {
    return convertFileSrc(pathOrUrl);
  }
  return pathOrUrl;
}

/// 메시지에서 {:name:} 패턴을 찾아 이모지 이미지로 치환
/// split(/\{:(\w+):\}/) 결과: ["앞텍스트", "이모지이름", "뒤텍스트", ...]
/// 홀수 인덱스 = 이모지 이름, 짝수 인덱스 = 일반 텍스트
function renderMessage(msg: string, emojis: Record<string, string>): React.ReactNode[] {
  const parts = msg.split(/\{:(\w+):\}/);
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      const url = emojis[part];
      if (url) {
        return (
          <img
            key={i}
            src={toDisplaySrc(url)}
            className="w-5 h-5 inline-block align-middle"
            alt={`:${part}:`}
          />
        );
      }
      return <span key={i}>{`{:${part}:}`}</span>;
    }
    return part ? <span key={i}>{part}</span> : null;
  });
}

// memo: 가상 스크롤 환경에서 props가 바뀌지 않은 항목의 불필요한 재렌더링 방지
export default memo(function ChatItem({ chat, showTimestamp, showBadges, onNicknameClick }: ChatItemProps) {
  const isDonation = chat.chat_type === "후원";
  const nickColor = isDonation ? "#ffcc00" : getUserColor(chat.uid, chat.color_code);

  return (
    <div
      className="flex flex-wrap items-baseline gap-x-1 px-2 py-0.5 rounded chat-text"
      style={isDonation ? { background: "var(--donation-bg)" } : undefined}
    >
      {/* 타임스탬프 */}
      {showTimestamp && (
        <span className="text-theme-muted shrink-0">[{chat.time}]</span>
      )}

      {/* 배지 (로컬 캐시 경로 or URL) */}
      {showBadges && chat.badges.length > 0 && (
        <span className="flex items-center gap-0.5 shrink-0">
          {chat.badges.slice(0, 3).map((url, i) => (
            <img key={i} src={toDisplaySrc(url)} className="w-4 h-4 inline-block" alt="" />
          ))}
        </span>
      )}

      {/* 닉네임 - 클릭 시 유저 필터 */}
      <span
        className="font-semibold shrink-0 cursor-pointer hover:underline"
        style={{ color: nickColor }}
        onClick={() => onNicknameClick?.(chat.uid, chat.nickname)}
      >
        {isDonation ? `[후원] ${chat.nickname}` : chat.nickname}
      </span>

      {/* 메시지 - {:name:} 이모지 치환 */}
      <span className="text-theme-primary break-all">
        : {renderMessage(chat.message, chat.emojis)}
      </span>
    </div>
  );
});
