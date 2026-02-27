import { getCurrentWindow } from "@tauri-apps/api/window";

interface MenuBarProps {
  donationOnly: boolean;
  showTimestamp: boolean;
  showBadges: boolean;
  fontSize: number;
  onToggleDonationOnly: () => void;
  onToggleTimestamp: () => void;
  onToggleBadges: () => void;
  onFontSizeChange: (size: number) => void;
  onClearChat: () => void;
}

export default function MenuBar({
  donationOnly,
  showTimestamp,
  showBadges,
  fontSize,
  onToggleDonationOnly,
  onToggleTimestamp,
  onToggleBadges,
  onFontSizeChange,
  onClearChat,
}: MenuBarProps) {
  return (
    <div className="flex bg-neutral-800 border-b border-neutral-700 text-sm select-none">
      {/* 앱 아이콘 */}
      <div className="flex items-center px-2">
        <img src="/img/chzzk.png" className="w-4 h-4" alt="Chzzk" />
      </div>
      {/* TODO: 메뉴바 버튼 직접 클릭시에, 메뉴가 펼쳐진상태로 다시 버튼클릭시엔 안닫힘. 버그같음*/}
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
          <div className="border-t border-neutral-700 my-0.5" />
          {/* 폰트 크기 */}
          <div className="flex items-center px-4 py-1.5 gap-2 text-neutral-200 whitespace-nowrap">
            <span className="flex-1">폰트 크기</span>
            <button
              onClick={() => onFontSizeChange(Math.max(10, fontSize - 1))}
              className="w-5 h-5 flex items-center justify-center hover:bg-neutral-600 rounded"
            >−</button>
            <span className="w-6 text-center text-neutral-400">{fontSize}</span>
            <button
              onClick={() => onFontSizeChange(Math.min(20, fontSize + 1))}
              className="w-5 h-5 flex items-center justify-center hover:bg-neutral-600 rounded"
            >+</button>
          </div>
        </div>
      </div>

      {/* 트레이 아이콘으로 버튼 */}
      <button
        onClick={() => getCurrentWindow().hide()}
        className="px-3 py-1.5 hover:bg-neutral-700 text-neutral-200"
        title="트레이 아이콘으로 최소화"
      >
        트레이 아이콘
      </button>

      {/* 도움말 - 삭제 예정, 임시 hidden */}
      <div className="menu-dropdown hidden">
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
