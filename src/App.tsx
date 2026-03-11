import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { ChatData } from "./types/chat";
import { Tab, MAX_TABS, newTab } from "./types/tab";
import MenuBar from "./components/MenuBar";
import TabBar from "./components/TabBar";
import ConnectionBar from "./components/ConnectionBar";
import StatusBar from "./components/StatusBar";
import ChatList from "./components/ChatList";

// ── DEV 더미 데이터 ─────────────────────────────────────────────────────────

let dummyCounter = 0;

interface DummyAssets {
  cacheFiles: string[];
  logEntries: { nickname: string; message: string; is_donation: boolean }[];
  emojiMap: Record<string, string>;
}

const dummyAssets: DummyAssets = { cacheFiles: [], logEntries: [], emojiMap: {} };

function makeDummyChat(counter: number): ChatData {
  const { cacheFiles, logEntries, emojiMap } = dummyAssets;
  const hasAssets = cacheFiles.length > 0;
  const entry = logEntries.length > 0 ? logEntries[counter % logEntries.length] : null;
  const userSlot = counter % 50;
  const numBadges = userSlot % 3;

  return {
    uid: `dummy_user_${userSlot}`,
    nickname: entry?.nickname ?? `유저${counter}`,
    message: entry?.message ?? `테스트 메시지 ${counter}번`,
    time: new Date().toTimeString().slice(0, 8),
    chat_type: (entry?.is_donation ?? counter % 7 === 0) ? "후원" : "채팅",
    color_code: ["", "SG001", "SG002", "SG004"][counter % 4],
    badges: hasAssets
      ? Array.from({ length: numBadges }, (_, i) => cacheFiles[(userSlot * 3 + i) % cacheFiles.length])
      : [],
    emojis: hasAssets ? { ...emojiMap } : {},
    subscription_month: userSlot === 0 ? 12 : 0,
    os_type: counter % 5 === 0 ? "MOBILE" : "PC",
    user_role: userSlot === 0 ? "manager" : "common_user",
  };
}

// ── 유틸 ────────────────────────────────────────────────────────────────────

function pushChats(prev: ChatData[], items: ChatData[]): ChatData[] {
  const next = [...prev, ...items];
  return next.length > 60000 ? next.slice(-50000) : next;
}

// ── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  // 탭 상태
  const [tabs, setTabs] = useState<Tab[]>(() => [newTab()]);
  const [activeTabId, setActiveTabId] = useState(() => tabs[0].tabId);

  // 현재 활성 탭 (파생값)
  const activeTab = tabs.find((t) => t.tabId === activeTabId) ?? tabs[0];

  // 전역 설정 상태
  const [donationOnly, setDonationOnly] = useState(false);
  const [showTimestamp, setShowTimestamp] = useState(true);
  const [showBadges, setShowBadges] = useState(true);
  const [fontSize, setFontSize] = useState(13);
  const [theme, setTheme] = useState("dark");

  // 설정 저장용 ref (stale closure 방지)
  const settingsRef = useRef({ font_size: 13, show_timestamp: true, show_badges: true, donation_only: false, theme: "dark" });

  // 활성 탭 ID ref (keydown 핸들러 등 closure 안에서 최신값 참조용)
  const activeTabIdRef = useRef(activeTabId);
  useEffect(() => { activeTabIdRef.current = activeTabId; }, [activeTabId]);

  // 탭별 이벤트 리스너 해제 함수 저장
  const unlistenMap = useRef<Map<string, () => void>>(new Map());

  // DEV 스트레스 테스트
  const stressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isStressTesting, setIsStressTesting] = useState(false);

  // ── 초기화 useEffect ───────────────────────────────────────────────────────

  // 설정 로드
  useEffect(() => {
    invoke<{ font_size: number; show_timestamp: boolean; show_badges: boolean; donation_only: boolean; theme: string }>(
      "get_settings"
    ).then((s) => {
      settingsRef.current = s;
      setFontSize(s.font_size);
      setShowTimestamp(s.show_timestamp);
      setShowBadges(s.show_badges);
      setDonationOnly(s.donation_only);
      setTheme(s.theme ?? "dark");
    });
  }, []);

  // 테마 적용
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // 폰트 크기 적용
  useEffect(() => {
    document.documentElement.style.setProperty("--chat-font-size", `${fontSize}px`);
  }, [fontSize]);

  // 더미 에셋 로드 (DEV)
  useEffect(() => {
    invoke<{
      cache_files: string[];
      log_entries: { nickname: string; message: string; is_donation: boolean }[];
    }>("get_dummy_assets").then((data) => {
      const emojiNames = new Set<string>();
      for (const entry of data.log_entries) {
        for (const m of entry.message.matchAll(/\{:(\w+):\}/g)) emojiNames.add(m[1]);
      }
      const emojiMap: Record<string, string> = {};
      [...emojiNames].forEach((name, i) => {
        if (data.cache_files.length > 0) emojiMap[name] = data.cache_files[i % data.cache_files.length];
      });
      dummyAssets.cacheFiles = data.cache_files;
      dummyAssets.logEntries = data.log_entries;
      dummyAssets.emojiMap = emojiMap;
    });
  }, []);

  // Ctrl+F: 활성 탭 검색 토글 / Escape: 검색 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tabId = activeTabIdRef.current;
      if (e.ctrlKey && e.key === "f") {
        e.preventDefault();
        setTabs((prev) => prev.map((t) =>
          t.tabId === tabId ? { ...t, showSearch: !t.showSearch } : t
        ));
      }
      if (e.key === "Escape") {
        setTabs((prev) => prev.map((t) =>
          t.tabId === tabId ? { ...t, showSearch: false, searchQuery: "" } : t
        ));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // 언마운트 시 모든 리스너 해제
  useEffect(() => {
    return () => { unlistenMap.current.forEach((fn) => fn()); };
  }, []);

  // ── 탭 조작 ───────────────────────────────────────────────────────────────

  const updateTab = (tabId: string, patch: Partial<Tab>) =>
    setTabs((prev) => prev.map((t) => t.tabId === tabId ? { ...t, ...patch } : t));

  const addTab = () => {
    if (tabs.length >= MAX_TABS) return;
    const tab = newTab();
    setTabs((prev) => [...prev, tab]);
    setActiveTabId(tab.tabId);
  };

  const closeTab = (tabId: string) => {
    const tab = tabs.find((t) => t.tabId === tabId);
    if (tab?.status === "connected") disconnectTab(tabId, tab.streamerUid);

    setTabs((prev) => {
      const next = prev.filter((t) => t.tabId !== tabId);
      return next.length > 0 ? next : [newTab()];
    });

    // 닫힌 탭이 활성 탭이었으면 다른 탭으로 전환
    if (activeTabId === tabId) {
      const other = tabs.find((t) => t.tabId !== tabId);
      if (other) setActiveTabId(other.tabId);
    }
  };

  // ── 연결/해제 ─────────────────────────────────────────────────────────────

  const connectTab = async (tabId: string, uid: string) => {
    updateTab(tabId, { status: "connecting", errorMsg: "" });
    try {
      const match = uid.match(/chzzk\.naver\.com\/(?:live\/)?([a-f0-9]+)/);
      const streamerUid = match ? match[1] : uid;

      const info = await invoke<{ channel_name: string }>("connect_chat", { streamerUid });

      // 탭별 독립 이벤트 리스너 등록
      const unlisten = await listen<ChatData>(`chat-message-${streamerUid}`, (event) => {
        setTabs((prev) => prev.map((t) =>
          t.tabId === tabId ? { ...t, chats: pushChats(t.chats, [event.payload]) } : t
        ));
      });
      unlistenMap.current.set(tabId, unlisten);

      updateTab(tabId, { status: "connected", streamerUid, channelName: info.channel_name });
    } catch (e) {
      updateTab(tabId, { status: "disconnected", errorMsg: typeof e === "string" ? e : JSON.stringify(e) });
    }
  };

  const disconnectTab = (tabId: string, streamerUid: string) => {
    invoke("disconnect_chat", { streamerUid });
    unlistenMap.current.get(tabId)?.();
    unlistenMap.current.delete(tabId);
    updateTab(tabId, { status: "idle", streamerUid: "", channelName: "", chats: [] });
  };

  // ── 설정 저장 ─────────────────────────────────────────────────────────────

  const applySettings = (patch: Partial<typeof settingsRef.current>) => {
    const next = { ...settingsRef.current, ...patch };
    settingsRef.current = next;
    invoke("save_settings", { s: next });
  };

  // ── DEV ───────────────────────────────────────────────────────────────────

  const addDummyMessage = () => {
    const tabId = activeTabId;
    setTabs((prev) => prev.map((t) =>
      t.tabId === tabId ? { ...t, chats: pushChats(t.chats, [makeDummyChat(++dummyCounter)]) } : t
    ));
  };

  const toggleStressTest = () => {
    if (stressIntervalRef.current) {
      clearInterval(stressIntervalRef.current);
      stressIntervalRef.current = null;
      setIsStressTesting(false);
    } else {
      setIsStressTesting(true);
      const targetTabId = activeTabId;
      stressIntervalRef.current = setInterval(() => {
        const batch = Array.from({ length: 100 }, () => makeDummyChat(++dummyCounter));
        setTabs((prev) => prev.map((t) =>
          t.tabId === targetTabId ? { ...t, chats: pushChats(t.chats, batch) } : t
        ));
      }, 1000);
    }
  };

  // ── JSX ───────────────────────────────────────────────────────────────────

  const isConnected = activeTab.status === "connected";
  const isConnecting = activeTab.status === "connecting";

  return (
    <div className="h-screen flex flex-col bg-theme-primary text-theme-primary overflow-hidden">
      <MenuBar
        donationOnly={donationOnly}
        showTimestamp={showTimestamp}
        showBadges={showBadges}
        fontSize={fontSize}
        theme={theme}
        onToggleDonationOnly={() => { const next = !donationOnly; setDonationOnly(next); applySettings({ donation_only: next }); }}
        onToggleTimestamp={() => { const next = !showTimestamp; setShowTimestamp(next); applySettings({ show_timestamp: next }); }}
        onToggleBadges={() => { const next = !showBadges; setShowBadges(next); applySettings({ show_badges: next }); }}
        onFontSizeChange={(size) => { setFontSize(size); applySettings({ font_size: size }); }}
        onThemeChange={(t) => { setTheme(t); applySettings({ theme: t }); }}
        onClearChat={() => updateTab(activeTabId, { chats: [] })}
      />

      <TabBar
        tabs={tabs}
        activeTabId={activeTabId}
        onSelect={setActiveTabId}
        onClose={closeTab}
        onAdd={addTab}
      />

      <ConnectionBar
        uid={activeTab.uid}
        isConnected={isConnected}
        isConnecting={isConnecting}
        onUidChange={(uid) => updateTab(activeTabId, { uid })}
        onToggleConnect={() =>
          isConnected
            ? disconnectTab(activeTabId, activeTab.streamerUid)
            : connectTab(activeTabId, activeTab.uid)
        }
      />

      <StatusBar status={activeTab.status} channelName={activeTab.channelName} count={activeTab.chats.length} />

      {activeTab.errorMsg && (
        <div className="px-2 py-1 text-xs text-red-400 bg-red-950 border-b border-red-800 break-all">
          {activeTab.errorMsg}
        </div>
      )}

      {/* 검색 바 */}
      {activeTab.showSearch && (
        <div className="px-2 py-1 bg-theme-secondary border-b border-theme flex gap-2">
          <input
            autoFocus
            value={activeTab.searchQuery}
            onChange={(e) => updateTab(activeTabId, { searchQuery: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === "Escape") updateTab(activeTabId, { showSearch: false, searchQuery: "" });
            }}
            placeholder="닉네임 / 메시지 검색..."
            className="flex-1 bg-theme-tertiary text-theme-primary placeholder-theme-muted text-xs px-2 py-1 rounded outline-none"
          />
          <button
            onClick={() => updateTab(activeTabId, { showSearch: false, searchQuery: "" })}
            className="text-theme-muted hover:text-theme-primary text-xs"
          >✕</button>
        </div>
      )}

      {/* 유저 필터 바 */}
      {activeTab.selectedUid && (
        <div className="px-2 py-1 bg-theme-tertiary border-b border-theme flex items-center text-xs">
          <span className="text-theme-secondary">
            👤 <span className="text-theme-primary">{activeTab.selectedNickname}</span> 메시지 내역
          </span>
          <button
            onClick={() => updateTab(activeTabId, { selectedUid: null })}
            className="ml-auto text-theme-muted hover:text-theme-primary"
          >✕</button>
        </div>
      )}

      <ChatList
        chats={activeTab.chats}
        showTimestamp={showTimestamp}
        showBadges={showBadges}
        donationOnly={donationOnly}
        searchQuery={activeTab.searchQuery}
        selectedUid={activeTab.selectedUid}
        onNicknameClick={(uid, nickname) =>
          updateTab(activeTabId, {
            selectedUid: activeTab.selectedUid === uid ? null : uid,
            selectedNickname: nickname,
          })
        }
      />

      {/* DEV */}
      <div className="px-2 py-1 bg-theme-deep border-t border-theme flex gap-3">
        <button onClick={addDummyMessage} className="text-xs text-theme-muted hover:text-theme-secondary">
          [DEV] 더미 1건
        </button>
        <button
          onClick={toggleStressTest}
          className={`text-xs ${isStressTesting ? "text-red-400 hover:text-red-300" : "text-theme-muted hover:text-theme-secondary"}`}
        >
          [DEV] 스트레스 {isStressTesting ? "중지 ■" : "시작 ▶ (100건/초)"}
        </button>
      </div>
    </div>
  );
}
