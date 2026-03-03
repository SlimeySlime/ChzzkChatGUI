import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
// getCurrentWindow().hide() 대신 hide_to_tray 커맨드 사용:
// 직접 hide()하면 창 상태(크기·위치) 저장 없이 숨겨짐 → Rust 커맨드에서 저장 후 숨김

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
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const menuBarRef = useRef<HTMLDivElement>(null);

  // 메뉴바 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      if (menuBarRef.current && !menuBarRef.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, []);

  const toggle = (name: string) => {
    setOpenMenu((prev) => (prev === name ? null : name));
  };

  // 메뉴 항목 클릭 시 액션 실행 + 드롭다운 닫기
  const handleAction = (fn: () => void) => {
    fn();
    setOpenMenu(null);
  };

  return (
    <div ref={menuBarRef} className="flex bg-neutral-800 border-b border-neutral-700 text-sm select-none">
      {/* 앱 아이콘 */}
      <div className="flex items-center px-2">
        <img src="/img/chzzk.png" className="w-4 h-4" alt="Chzzk" />
      </div>

      {/* 옵션 */}
      <div className="menu-dropdown">
        <button
          onClick={() => toggle("options")}
          className="px-3 py-1.5 hover:bg-neutral-700 text-neutral-200"
        >
          옵션
        </button>
        {openMenu === "options" && (
          <div className="menu-panel bg-neutral-800 border border-neutral-700 rounded shadow-lg">
            <button
              onClick={() => handleAction(onToggleDonationOnly)}
              className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200 whitespace-nowrap"
            >
              {donationOnly ? "✓ " : "\u00A0\u00A0\u00A0"}후원만 보기
            </button>
            <div className="border-t border-neutral-700 my-0.5" />
            <button
              onClick={() => handleAction(onClearChat)}
              className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200"
            >
              &nbsp;&nbsp;&nbsp;채팅 초기화
            </button>
          </div>
        )}
      </div>

      {/* 설정 */}
      <div className="menu-dropdown">
        <button
          onClick={() => toggle("settings")}
          className="px-3 py-1.5 hover:bg-neutral-700 text-neutral-200"
        >
          설정
        </button>
        {openMenu === "settings" && (
          <div className="menu-panel bg-neutral-800 border border-neutral-700 rounded shadow-lg">
            <button
              onClick={() => handleAction(onToggleTimestamp)}
              className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200 whitespace-nowrap"
            >
              {showTimestamp ? "✓ " : "\u00A0\u00A0\u00A0"}타임스탬프
            </button>
            <button
              onClick={() => handleAction(onToggleBadges)}
              className="w-full text-left px-4 py-1.5 hover:bg-neutral-700 text-neutral-200"
            >
              {showBadges ? "✓ " : "\u00A0\u00A0\u00A0"}배지
            </button>
            <div className="border-t border-neutral-700 my-0.5" />
            {/* 폰트 크기: 슬라이더형이므로 메뉴 닫지 않음 */}
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
        )}
      </div>

      {/* 트레이 아이콘으로 버튼 */}
      <button
        onClick={() => invoke("hide_to_tray")}
        className="px-3 py-1.5 hover:bg-neutral-700 text-neutral-200"
        title="트레이 아이콘으로 최소화"
      >
        트레이 아이콘
      </button>
    </div>
  );
}
