interface MenuBarProps {
  donationOnly: boolean;
  showTimestamp: boolean;
  showBadges: boolean;
  onToggleDonationOnly: () => void;
  onToggleTimestamp: () => void;
  onToggleBadges: () => void;
  onClearChat: () => void;
}

export default function MenuBar({
  donationOnly,
  showTimestamp,
  showBadges,
  onToggleDonationOnly,
  onToggleTimestamp,
  onToggleBadges,
  onClearChat,
}: MenuBarProps) {
  return (
    <div className="flex bg-neutral-800 border-b border-neutral-700 text-sm select-none">
      {/* 옵션 */}
      <div className="menu-dropdown">
        <button className="px-3 py-1.5 hover:bg-neutral-700 text-neutral-200">
          옵션
        </button>
        <div className="menu-panel bg-neutral-800 border border-neutral-700 rounded shadow-lg">
          <button
            onClick={onToggleDonationOnly}
            className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200 whitespace-nowrap"
          >
            {donationOnly ? "✓ " : "\u00A0\u00A0\u00A0"}후원만 보기
          </button>
          <div className="border-t border-neutral-700 my-0.5" />
          <button
            onClick={onClearChat}
            className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200"
          >
            &nbsp;&nbsp;&nbsp;채팅 초기화
          </button>
        </div>
      </div>

      {/* 설정 */}
      <div className="menu-dropdown">
        <button className="px-3 py-1.5 hover:bg-neutral-700 text-neutral-200">
          설정
        </button>
        <div className="menu-panel bg-neutral-800 border border-neutral-700 rounded shadow-lg">
          <button
            onClick={onToggleTimestamp}
            className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200 whitespace-nowrap"
          >
            {showTimestamp ? "✓ " : "\u00A0\u00A0\u00A0"}타임스탬프
          </button>
          <button
            onClick={onToggleBadges}
            className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200"
          >
            {showBadges ? "✓ " : "\u00A0\u00A0\u00A0"}배지
          </button>
        </div>
      </div>

      {/* 도움말 */}
      <div className="menu-dropdown">
        <button className="px-3 py-1.5 hover:bg-neutral-700 text-neutral-200">
          도움말
        </button>
        <div className="menu-panel bg-neutral-800 border border-neutral-700 rounded shadow-lg">
          <button className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-400 whitespace-nowrap">
            &nbsp;&nbsp;&nbsp;버그 리포트
          </button>
        </div>
      </div>
    </div>
  );
}
