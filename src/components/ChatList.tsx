import { useEffect, useRef } from "react";
import { ChatData } from "../types/chat";
import ChatItem from "./ChatItem";

interface ChatListProps {
  chats: ChatData[];
  showTimestamp: boolean;
  showBadges: boolean;
  donationOnly: boolean;
}

export default function ChatList({ chats, showTimestamp, showBadges, donationOnly }: ChatListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const atBottomRef = useRef(true);   // useState와 달리 렌더링없이 값 유지

  // 새 메시지 도착 시 자동 스크롤
  useEffect(() => {
    if (atBottomRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [chats]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 10;
  };

  const visible = donationOnly
    ? chats.filter((c) => c.chat_type === "후원")
    : chats;

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto py-1"
    >
      {visible.map((chat, i) => (
        <ChatItem
          key={i}
          chat={chat}
          showTimestamp={showTimestamp}
          showBadges={showBadges}
        />
      ))}
    </div>
  );
}