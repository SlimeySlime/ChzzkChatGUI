export interface ChatData {
  uid: string;
  nickname: string;
  message: string;
  time: string;
  chat_type: "채팅" | "후원";
  color_code: string;        // "SG001"~"SG009" | ""
  badges: string[];          // 이미지 URL 목록 (최대 3개)
  subscription_month: number;
  os_type: "PC" | "MOBILE";
  user_role: "common_user" | "manager" | "streamer";
}

export const COLOR_CODE_MAP: Record<string, string> = {
  SG001: "#8bff00",
  SG002: "#00ffff",
  SG003: "#ff00ff",
  SG004: "#ffff00",
  SG005: "#ff8800",
  SG006: "#ff0088",
  SG007: "#00aaff",
  SG008: "#aa00ff",
  SG009: "#ff0000",
};

export const USER_COLOR_PALETTE = [
  "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
  "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
  "#BB8FCE", "#82E0AA", "#F1948A", "#85C1E9",
];

export function getUserColor(uid: string, colorCode: string): string {
  if (COLOR_CODE_MAP[colorCode]) return COLOR_CODE_MAP[colorCode];
  const idx = [...uid].reduce((a, c) => a + c.charCodeAt(0), 0);
  return USER_COLOR_PALETTE[idx % USER_COLOR_PALETTE.length];
}
