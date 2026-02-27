import { useEffect, useRef } from "react";
import { ChatData } from "../types/chat";
import ChatItem from "./ChatItem";

interface ChatListProps {
  chats: ChatData[];
  showTimestamp: boolean;
  showBadges: boolean;
  donationOnly: boolean;
  searchQuery: string;
  selectedUid: string | null;
  onNicknameClick: (uid: string, nickname: string) => void;
}

export default function ChatList({
  chats,
  showTimestamp,
  showBadges,
  donationOnly,
  searchQuery,
  selectedUid,
  onNicknameClick,
}: ChatListProps) {
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

  // 필터 적용: donationOnly → selectedUid(최근 500건) → searchQuery
  let visible = donationOnly
    ? chats.filter((c) => c.chat_type === "후원")
    : chats;

  if (selectedUid) {
    // 유저별 이력: 해당 유저 메시지만, 최근 500건으로 제한 (메모리 관리)
    visible = visible.filter((c) => c.uid === selectedUid).slice(-500);
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    visible = visible.filter(
      (c) =>
        c.nickname.toLowerCase().includes(q) ||
        c.message.toLowerCase().includes(q)
    );
  }

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
          onNicknameClick={onNicknameClick}
        />
      ))}
    </div>
  );
}
