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
  const atBottomRef = useRef(true);       // useState와 달리 렌더링없이 값 유지
  const isProgrammaticRef = useRef(false); // 코드에서 강제 스크롤 중임을 표시

  // 새 메시지 도착 시 자동 스크롤
  // 문제: scrollTop 대입이 scroll 이벤트를 발생시키고, handleScroll이 레이아웃 반영 전
  //       타이밍에 atBottomRef를 false로 잘못 설정하는 race condition이 있었음
  // 해결: 코드가 직접 스크롤하는 동안은 handleScroll을 무시하도록 플래그 사용
  useEffect(() => {
    if (!atBottomRef.current || !containerRef.current) return;
    isProgrammaticRef.current = true;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
    // scroll 이벤트가 동기적으로 발생하므로 setTimeout(0)으로 플래그 해제
    setTimeout(() => { isProgrammaticRef.current = false; }, 0);
  }, [chats]);

  const handleScroll = () => {
    if (isProgrammaticRef.current) return; // 자동 스크롤 중 발생한 이벤트 무시
    const el = containerRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
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
