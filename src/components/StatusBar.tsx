export type ConnectionStatus = "idle" | "connecting" | "connected" | "disconnected";

interface StatusBarProps {
  status: ConnectionStatus;
  channelName: string;
  count: number;
}

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  idle: "대기 중",
  connecting: "연결 중...",
  connected: "연결 완료",
  disconnected: "연결 끊김",
};

const STATUS_COLOR: Record<ConnectionStatus, string> = {
  idle: "text-neutral-500",
  connecting: "text-yellow-400",
  connected: "text-green-400",
  disconnected: "text-red-400",
};

export default function StatusBar({ status, channelName, count }: StatusBarProps) {
  return (
    <div className="flex items-center justify-between px-2 py-0.5 bg-neutral-900 border-b border-neutral-700 text-xs">
      <span className={STATUS_COLOR[status]}>
        {STATUS_LABEL[status]}
        {status === "connected" && channelName && ` — ${channelName}`}
      </span>
      <span className="text-neutral-500">{count.toLocaleString()}건</span>
    </div>
  );
}