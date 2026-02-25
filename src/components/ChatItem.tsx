import { ChatData, getUserColor } from "../types/chat";

interface ChatItemProps {
  chat: ChatData;
  showTimestamp: boolean;
  showBadges: boolean;
}

export default function ChatItem({ chat, showTimestamp, showBadges }: ChatItemProps) {
  const isDonation = chat.chat_type === "후원";
  const nickColor = isDonation ? "#ffcc00" : getUserColor(chat.uid, chat.color_code);

  return (
    <div
      className="flex flex-wrap items-baseline gap-x-1 px-2 py-0.5 rounded chat-text"
      style={isDonation ? { background: "rgba(255, 204, 0, 0.12)" } : undefined}
    >
      {/* 타임스탬프 */}
      {showTimestamp && (
        <span className="text-neutral-500 shrink-0">[{chat.time}]</span>
      )}

      {/* 배지 (이미지 URL이 실제로 있을 때만 표시, Phase 5에서 구현) */}
      {showBadges && chat.badges.length > 0 && (
        <span className="flex items-center gap-0.5 shrink-0">
          {chat.badges.slice(0, 3).map((url, i) => (
            <img key={i} src={url} className="w-4 h-4 inline-block" alt="" />
          ))}
        </span>
      )}

      {/* 닉네임 */}
      <span className="font-semibold shrink-0" style={{ color: nickColor }}>
        {isDonation ? `[후원] ${chat.nickname}` : chat.nickname}
      </span>

      {/* 메시지 */}
      <span className="text-neutral-100 break-all">: {chat.message}</span>
    </div>
  );
}