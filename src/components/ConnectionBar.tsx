interface ConnectionBarProps {
  uid: string;
  isConnected: boolean;
  isConnecting: boolean;
  onUidChange: (uid: string) => void;
  onToggleConnect: () => void;
}

export default function ConnectionBar({
  uid,
  isConnected,
  isConnecting,
  onUidChange,
  onToggleConnect,
}: ConnectionBarProps) {
  const btnColor = isConnected
    ? "bg-red-600 hover:bg-red-500"
    : "bg-green-700 hover:bg-green-600";
  const btnLabel = isConnecting ? "연결 중..." : isConnected ? "해제" : "연결"; 

  return (
    <div className="flex gap-2 px-2 py-1.5 bg-neutral-900 border-b border-neutral-700">
      <input
        type="text"
        value={uid}
        onChange={(e) => onUidChange(e.target.value)}
        placeholder="스트리머 UID 또는 URL 입력"
        disabled={isConnected || isConnecting}
        className="flex-1 bg-neutral-800 text-neutral-100 placeholder-neutral-500 border border-neutral-700 rounded px-3 py-1 text-sm focus:outline-none focus:border-neutral-500 disabled:opacity-50"
      />
      <button
        onClick={onToggleConnect}
        disabled={isConnecting}
        className={`px-4 py-1 rounded text-sm font-semibold text-white transition-colors disabled:opacity-50 ${btnColor}`}
      >
        {btnLabel}
      </button>
    </div>
  );
}