import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { ChatData } from "./types/chat";
import MenuBar from "./components/MenuBar";
import ConnectionBar from "./components/ConnectionBar";
import StatusBar, { ConnectionStatus } from "./components/StatusBar";
import ChatList from "./components/ChatList";

let dummyCounter = 0;

export default function App() {
  const [uid, setUid] = useState("");
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [channelName, setChannelName] = useState("");
  const [chats, setChats] = useState<ChatData[]>([]);
  const [errorMsg, setErrorMsg] = useState("");

  // 메뉴 상태
  const [donationOnly, setDonationOnly] = useState(false);
  const [showTimestamp, setShowTimestamp] = useState(true);
  const [showBadges, setShowBadges] = useState(true);

  const isConnected = status === "connected";
  const isConnecting = status === "connecting";

  // Rust에서 emit("chat-message", ...) 이벤트 수신
  useEffect(() => {
    const unlisten = listen<ChatData>("chat-message", (event) => {
      setChats((prev) => {
        const next = [...prev, event.payload];
        return next.length > 12000 ? next.slice(-10000) : next; // 최대 10,000건
        // 슬라이싱은 1만건 초과마다 매번x. 12,000건으로 조금 널널하게
      });
    });
    return () => { unlisten.then((fn) => fn()); };
    // unlisten.then 구문이 잘 이해안가
  }, []);

  const handleToggleConnect = async () => {
    if (isConnected) {
      invoke("disconnect_chat");
      setStatus("idle");
      setChannelName("");
    } else {
      setStatus("connecting");
      setErrorMsg("");
      try {
        // URL 입력도 허용: https://chzzk.naver.com/live/<uid>
        const match = uid.match(/chzzk\.naver\.com\/(?:live\/)?([a-f0-9]+)/);
        const streamerUid = match ? match[1] : uid;

        const info = await invoke<{
          channel_name: string;
          chat_channel_id: string;
        }>("connect_chat", { streamerUid });
        setStatus("connected");
        setChannelName(info.channel_name);
      } catch (e) {
        const msg = typeof e === "string" ? e : JSON.stringify(e);
        setErrorMsg(msg);
        setStatus("disconnected");
      }
    }
  };

  // 더미 메시지 추가 (자동 스크롤 테스트용)
  const addDummyMessage = () => {
    dummyCounter++;
    const isDonation = dummyCounter % 7 === 0;
    setChats((prev) => [
      ...prev,
      {
        uid: `user${(dummyCounter % 6) + 1}01`,
        nickname: `유저${dummyCounter}`,
        message: `테스트 메시지 ${dummyCounter}번`,
        time: new Date().toTimeString().slice(0, 8),
        chat_type: isDonation ? "후원" : "채팅",
        color_code: ["", "SG001", "SG002", "SG004"][dummyCounter % 4],
        badges: [],
        subscription_month: 0,
        os_type: "PC",
        user_role: "common_user",
      },
    ]);
  };

  return (
    <div className="h-screen flex flex-col bg-neutral-900 text-white overflow-hidden">
      <MenuBar
        donationOnly={donationOnly}
        showTimestamp={showTimestamp}
        showBadges={showBadges}
        onToggleDonationOnly={() => setDonationOnly((v) => !v)}
        onToggleTimestamp={() => setShowTimestamp((v) => !v)}
        onToggleBadges={() => setShowBadges((v) => !v)}
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
      <ChatList
        chats={chats}
        showTimestamp={showTimestamp}
        showBadges={showBadges}
        donationOnly={donationOnly}
      />

      {/* 개발용: 더미 메시지 추가 버튼 */}
      <div className="px-2 py-1 bg-neutral-950 border-t border-neutral-800">
        <button
          onClick={addDummyMessage}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          [DEV] 더미 메시지 추가
        </button>
      </div>
    </div>
  );
}
