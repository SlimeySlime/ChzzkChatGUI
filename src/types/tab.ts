import { ChatData } from "./chat";
import { ConnectionStatus } from "../components/StatusBar";

export interface Tab {
  tabId: string;
  uid: string;             // 입력 필드값 (URL 또는 uid)
  streamerUid: string;     // 연결된 실제 streamer uid
  channelName: string;
  status: ConnectionStatus;
  errorMsg: string;
  chats: ChatData[];
  searchQuery: string;
  showSearch: boolean;
  selectedUid: string | null;
  selectedNickname: string;
}

export const MAX_TABS = 5;

let tabCounter = 0;

export function newTab(): Tab {
  return {
    tabId: `tab-${++tabCounter}`,
    uid: "",
    streamerUid: "",
    channelName: "",
    status: "idle",
    errorMsg: "",
    chats: [],
    searchQuery: "",
    showSearch: false,
    selectedUid: null,
    selectedNickname: "",
  };
}