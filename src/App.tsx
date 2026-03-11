import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { ChatData } from "./types/chat";
import MenuBar from "./components/MenuBar";
import ConnectionBar from "./components/ConnectionBar";
import StatusBar, { ConnectionStatus } from "./components/StatusBar";
import ChatList from "./components/ChatList";

let dummyCounter = 0;

interface DummyAssets {
  cacheFiles: string[];
  logEntries: { nickname: string; message: string; is_donation: boolean }[];
  // 로그에서 추출한 이모지 이름 → 캐시 파일 경로 매핑
  // 채널 이모지 세트 전체를 매 메시지에 담는 API 동작을 시뮬레이션
  emojiMap: Record<string, string>;
}

const dummyAssets: DummyAssets = { cacheFiles: [], logEntries: [], emojiMap: {} };

function makeDummyChat(counter: number): ChatData {
  const { cacheFiles, logEntries, emojiMap } = dummyAssets;
  const hasAssets = cacheFiles.length > 0;

  const entry = logEntries.length > 0
    ? logEntries[counter % logEntries.length]
    : null;

  const nickname = entry?.nickname ?? `유저${counter}`;
  const message  = entry?.message  ?? `테스트 메시지 ${counter}번`;
  const isDonation = entry?.is_donation ?? counter % 7 === 0;

  // 배지: 캐시 파일에서 0~2개 선택 (유저 인덱스 기반)
  const userSlot = counter % 50;
  const numBadges = userSlot % 3;
  const badges = hasAssets
    ? Array.from({ length: numBadges }, (_, i) =>
        cacheFiles[(userSlot * 3 + i) % cacheFiles.length]
      )
    : [];

  // 이모지: 채널 전체 이모지 세트 복사 (API 동작과 동일하게 매 메시지에 전체 포함)
  const emojis = hasAssets ? { ...emojiMap } : {};

  return {
    uid: `dummy_user_${userSlot}`,
    nickname,
    message,
    time: new Date().toTimeString().slice(0, 8),
    chat_type: isDonation ? "후원" : "채팅",
    color_code: ["", "SG001", "SG002", "SG004"][counter % 4],
    badges,
    emojis,
    subscription_month: userSlot === 0 ? 12 : 0,
    os_type: counter % 5 === 0 ? "MOBILE" : "PC",
    user_role: userSlot === 0 ? "manager" : "common_user",
  };
}

function pushChats(prev: ChatData[], items: ChatData[]): ChatData[] {
  const next = [...prev, ...items];
  return next.length > 60000 ? next.slice(-50000) : next;
}

export default function App() {
  const [uid, setUid] = useState("");
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [channelName, setChannelName] = useState("");
  const [chats, setChats] = useState<ChatData[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  // 메뉴/설정 상태
  const [donationOnly, setDonationOnly] = useState(false);
  const [showTimestamp, setShowTimestamp] = useState(true);
  const [showBadges, setShowBadges] = useState(true);
  const [fontSize, setFontSize] = useState(13);
  const [theme, setTheme] = useState("dark");

  // 검색 상태
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);

  // 유저 필터 상태
  const [selectedUid, setSelectedUid] = useState<string | null>(null);
  const [selectedNickname, setSelectedNickname] = useState("");

  // 최신 설정값을 항상 참조하기 위한 ref (saveSettings에서 stale closure 방지)
  const settingsRef = useRef({ font_size: 13, show_timestamp: true, show_badges: true, donation_only: false, theme: "dark" });

  const isConnected = status === "connected";
  const isConnecting = status === "connecting";

  // 앱 시작 시 settings.json 로드 (1회)
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

  // 테마 변경 시 HTML 요소에 data-theme 속성 적용
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // 더미 테스트용 에셋 로드 (1회): 실제 캐시 이미지 + 로그 닉네임/메시지
  useEffect(() => {
    invoke<{
      cache_files: string[];
      log_entries: { nickname: string; message: string; is_donation: boolean }[];
    }>("get_dummy_assets").then((data) => {
      // 로그 메시지에서 실제 사용된 이모지 이름 추출 ({:name:} 패턴)
      const emojiPattern = /\{:(\w+):\}/g;
      const emojiNames = new Set<string>();
      for (const entry of data.log_entries) {
        for (const m of entry.message.matchAll(emojiPattern)) {
          emojiNames.add(m[1]);
        }
      }
      // 이모지 이름 → 캐시 파일 경로 (round-robin 매핑)
      // 정확한 매핑은 아니지만 실제 이미지가 로드되어 메모리 동작을 테스트할 수 있음
      const emojiMap: Record<string, string> = {};
      [...emojiNames].forEach((name, i) => {
        if (data.cache_files.length > 0) {
          emojiMap[name] = data.cache_files[i % data.cache_files.length];
        }
      });

      dummyAssets.cacheFiles = data.cache_files;
      dummyAssets.logEntries = data.log_entries;
      dummyAssets.emojiMap = emojiMap;
    });
  }, []);

  // 폰트 크기 CSS 변수 동기화
  useEffect(() => {
    document.documentElement.style.setProperty("--chat-font-size", `${fontSize}px`);
  }, [fontSize]);

  // Rust에서 emit("chat-message", ...) 이벤트 수신
  useEffect(() => {
    const unlisten = listen<ChatData>("chat-message", (event) => {
      // Q. setChats([...chats, event.payload]) 하는것과 pushChats 메서드를 사용하는것의 차이는 뭐야?
      // pushChats는 단순히 slicing 기능만 하는거 아냐?
      setChats((prev) => pushChats(prev, [event.payload]));
    });
    // listen이 Promise<UnlistenFn> 을 반환하기 때문에, .then((fn) => fn()) 형태로 비동기처리
    return () => { unlisten.then((fn) => fn()); };
  }, []);

  // Ctrl+F: 검색 바 토글 / Escape: 검색 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "f") {
        e.preventDefault();
        setShowSearch((prev) => !prev);
      }
      if (e.key === "Escape") {
        setShowSearch(false);
        setSearchQuery("");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // 설정 변경 + 즉시 저장. ref를 통해 항상 최신값을 유지
  const applySettings = (patch: Partial<typeof settingsRef.current>) => {
    const next = { ...settingsRef.current, ...patch };
    settingsRef.current = next;
    invoke("save_settings", { s: next });
  };

  const handleToggleConnect = async () => {
    if (isConnected) {
      invoke("disconnect_chat");
      setStatus("idle");
      setChannelName("");
    } else {
      setStatus("connecting");
      setErrorMsg("");
      try {
        const match = uid.match(/chzzk\.naver\.com\/(?:live\/)?([a-f0-9]+)/);
        const streamerUid = match ? match[1] : uid;
        const info = await invoke<{ channel_name: string; chat_channel_id: string }>(
          "connect_chat", { streamerUid }
        );
        setStatus("connected");
        setChannelName(info.channel_name);
      } catch (e) {
        const msg = typeof e === "string" ? e : JSON.stringify(e);
        setErrorMsg(msg);
        setStatus("disconnected");
      }
    }
  };

  // 닉네임 클릭 → 유저 필터 (같은 유저 재클릭 시 해제)
  const handleNicknameClick = (uid: string, nickname: string) => {
    setSelectedUid((prev) => (prev === uid ? null : uid));
    setSelectedNickname(nickname);
  };

  // 스트레스 테스트 interval ref
  const stressIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // useRef<ReturnType<typeof setInterval> | null> 과 같은 복잡한 방식이 권장되는 일반적인 방식이야? 내가 잘 모르는걸까
  const [isStressTesting, setIsStressTesting] = useState(false);

  // 더미 메시지 1건 추가 (자동 스크롤 테스트용)
  const addDummyMessage = () => {
    setChats((prev) => pushChats(prev, [makeDummyChat(++dummyCounter)]));
  };

  // 스트레스 테스트: 1초마다 100건 배치 추가, 60000건 초과 시 50000건으로 컷팅
  const toggleStressTest = () => {
    if (stressIntervalRef.current) {
      clearInterval(stressIntervalRef.current);
      stressIntervalRef.current = null;
      setIsStressTesting(false);
    } else {
      setIsStressTesting(true);
      stressIntervalRef.current = setInterval(() => {
        const batch = Array.from({ length: 100 }, () => makeDummyChat(++dummyCounter));
        setChats((prev) => pushChats(prev, batch));
      }, 1000);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-theme-primary text-theme-primary overflow-hidden">
      <MenuBar
        donationOnly={donationOnly}
        showTimestamp={showTimestamp}
        showBadges={showBadges}
        fontSize={fontSize}
        theme={theme}
        onToggleDonationOnly={() => {
          const next = !donationOnly;
          setDonationOnly(next);
          applySettings({ donation_only: next });
        }}
        onToggleTimestamp={() => {
          const next = !showTimestamp;
          setShowTimestamp(next);
          applySettings({ show_timestamp: next });
        }}
        onToggleBadges={() => {
          const next = !showBadges;
          setShowBadges(next);
          applySettings({ show_badges: next });
        }}
        onFontSizeChange={(size) => {
          setFontSize(size);
          applySettings({ font_size: size });
        }}
        onThemeChange={(t) => {
          setTheme(t);
          applySettings({ theme: t });
        }}
        onClearChat={() => setChats([])}
      />
      <ConnectionBar
        uid={uid}
        isConnected={isConnected}
        isConnecting={isConnecting}
        onUidChange={setUid}
        onToggleConnect={handleToggleConnect}
      />
      <StatusBar status={status} channelName={channelName} count={chats.length} />
      {errorMsg && (
        <div className="px-2 py-1 text-xs text-red-400 bg-red-950 border-b border-red-800 break-all">
          {errorMsg}
        </div>
      )}

      {/* 검색 바 - Ctrl+F로 열기/닫기 */}
      {showSearch && (
        <div className="px-2 py-1 bg-theme-secondary border-b border-theme flex gap-2">
          <input
            autoFocus
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") { setShowSearch(false); setSearchQuery(""); }
            }}
            placeholder="닉네임 / 메시지 검색..."
            className="flex-1 bg-theme-tertiary text-theme-primary placeholder-theme-muted text-xs px-2 py-1 rounded outline-none"
          />
          <button
            onClick={() => { setShowSearch(false); setSearchQuery(""); }}
            className="text-theme-muted hover:text-theme-primary text-xs"
          >✕</button>
        </div>
      )}

      {/* 유저 필터 바 - 닉네임 클릭 시 표시 */}
      {selectedUid && (
        <div className="px-2 py-1 bg-theme-tertiary border-b border-theme flex items-center text-xs">
          <span className="text-theme-secondary">
            👤 <span className="text-theme-primary">{selectedNickname}</span> 메시지 내역
          </span>
          <button
            onClick={() => setSelectedUid(null)}
            className="ml-auto text-theme-muted hover:text-theme-primary"
          >✕</button>
        </div>
      )}

      <ChatList
        chats={chats}
        showTimestamp={showTimestamp}
        showBadges={showBadges}
        donationOnly={donationOnly}
        searchQuery={searchQuery}
        selectedUid={selectedUid}
        onNicknameClick={handleNicknameClick}
      />

      {/* 개발용: 더미 메시지 추가 버튼 */}
      <div className="px-2 py-1 bg-theme-deep border-t border-theme flex gap-3">
        <button
          onClick={addDummyMessage}
          className="text-xs text-theme-muted hover:text-theme-secondary"
        >
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
