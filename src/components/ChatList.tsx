import { useEffect, useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
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
  const atBottomRef = useRef(true);
  const isProgrammaticRef = useRef(false);

  // 필터 적용: donationOnly → selectedUid(최근 500건) → searchQuery
  let visible = donationOnly
    ? chats.filter((c) => c.chat_type === "후원")
    : chats;

  if (selectedUid) {
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

  const virtualizer = useVirtualizer({
    count: visible.length,
    getScrollElement: () => containerRef.current,
    // 채팅 아이템 기본 높이 추정값 (실제 높이는 measureElement가 측정)
    estimateSize: () => 28,
    // 뷰포트 밖 위아래로 추가 렌더링할 항목 수 (빠른 스크롤 시 공백 방지)
    overscan: 10,
  });

  // 새 메시지 도착 시 최하단 자동 스크롤
  // isProgrammaticRef: scrollToIndex가 유발하는 scroll 이벤트가
  //                    atBottomRef를 잘못 변경하지 않도록 보호
  useEffect(() => {
    if (!atBottomRef.current || visible.length === 0) return;
    isProgrammaticRef.current = true;
    virtualizer.scrollToIndex(visible.length - 1, { behavior: "auto" });
    setTimeout(() => { isProgrammaticRef.current = false; }, 0);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible.length]);

  const handleScroll = () => {
    if (isProgrammaticRef.current) return;
    const el = containerRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
  };

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto py-1"
    >
      {/* 가상 스크롤 컨테이너: 전체 높이를 유지해 스크롤바가 정확하게 표시됨 */}
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {/* 실제 DOM에는 뷰포트 근처 항목만 렌더링 */}
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            data-index={virtualItem.index}
            ref={virtualizer.measureElement}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <ChatItem
              chat={visible[virtualItem.index]}
              showTimestamp={showTimestamp}
              showBadges={showBadges}
              onNicknameClick={onNicknameClick}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
