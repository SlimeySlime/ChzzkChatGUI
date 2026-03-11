import { Tab, MAX_TABS } from "../types/tab";

interface TabBarProps {
  tabs: Tab[];
  activeTabId: string;
  onSelect: (tabId: string) => void;
  onClose: (tabId: string) => void;
  onAdd: () => void;
}

export default function TabBar({ tabs, activeTabId, onSelect, onClose, onAdd }: TabBarProps) {
  return (
    <div className="flex bg-theme-deep border-b border-theme text-xs select-none overflow-x-auto shrink-0">
      {tabs.map((tab) => (
        <div
          key={tab.tabId}
          onClick={() => onSelect(tab.tabId)}
          className={`flex items-center gap-1.5 px-3 py-1.5 border-r border-theme cursor-pointer shrink-0
            ${tab.tabId === activeTabId
              ? "bg-theme-primary"
              : "bg-theme-deep hover:bg-theme-secondary"}`}
        >
          {/* 연결 상태 표시 점 */}
          <span className={tab.status === "connected" ? "text-green-400" : "text-theme-muted"}>●</span>
          <span className="text-theme-secondary max-w-28 truncate">
            {tab.channelName || "새 탭"}
          </span>
          {/* 탭이 2개 이상일 때만 닫기 버튼 표시 */}
          {tabs.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); onClose(tab.tabId); }}
              className="text-theme-muted hover:text-theme-primary ml-1"
            >✕</button>
          )}
        </div>
      ))}

      {/* 탭 추가 버튼 (최대 탭 수 미만일 때만) */}
      {tabs.length < MAX_TABS && (
        <button
          onClick={onAdd}
          className="px-3 py-1.5 text-theme-muted hover:text-theme-primary hover:bg-theme-secondary"
        >＋</button>
      )}
    </div>
  );
}
