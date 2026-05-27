import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

interface CookieDialogProps {
  onClose: () => void;
}

export default function CookieDialog({ onClose }: CookieDialogProps) {
  const [nidAut, setNidAut] = useState("");
  const [nidSes, setNidSes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  // 현재 저장된 쿠키 불러오기
  useEffect(() => {
    invoke<{ nid_aut: string; nid_ses: string }>("get_cookies").then((c) => {
      setNidAut(c.nid_aut);
      setNidSes(c.nid_ses);
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    if (!nidAut.trim() || !nidSes.trim()) {
      setError("NID_AUT와 NID_SES를 모두 입력해주세요.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await invoke("save_cookies", { nidAut: nidAut.trim(), nidSes: nidSes.trim() });
      setSaved(true);
      setTimeout(() => onClose(), 800);
    } catch (e) {
      setError(typeof e === "string" ? e : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  // Escape 키로 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    // 배경 오버레이
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-theme-secondary border border-theme rounded-lg shadow-2xl w-[420px] max-w-[90vw] p-5 flex flex-col gap-4 select-text">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <h2 className="text-theme-primary font-semibold text-sm">네이버 쿠키 설정</h2>
          <button
            onClick={onClose}
            className="text-theme-muted hover:text-theme-primary text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {/* 안내 */}
        <p className="text-xs text-theme-muted leading-relaxed">
          Chzzk 채팅 연결에 네이버 로그인 쿠키가 필요합니다.<br />
          Chrome → F12 → Application → Cookies → <strong className="text-theme-secondary">nid.naver.com</strong><br />
          에서 <strong className="text-theme-secondary">NID_AUT</strong>와 <strong className="text-theme-secondary">NID_SES</strong> 값을 복사하세요.
        </p>

        {/* NID_AUT */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-theme-secondary">NID_AUT</label>
          <input
            type="text"
            value={nidAut}
            onChange={(e) => setNidAut(e.target.value)}
            placeholder="NID_AUT 값 입력..."
            className="bg-theme-tertiary text-theme-primary placeholder-theme-muted text-xs px-3 py-2 rounded outline-none border border-transparent focus:border-blue-500 font-mono"
            spellCheck={false}
          />
        </div>

        {/* NID_SES */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-theme-secondary">NID_SES</label>
          <input
            type="text"
            value={nidSes}
            onChange={(e) => setNidSes(e.target.value)}
            placeholder="NID_SES 값 입력..."
            className="bg-theme-tertiary text-theme-primary placeholder-theme-muted text-xs px-3 py-2 rounded outline-none border border-transparent focus:border-blue-500 font-mono"
            spellCheck={false}
          />
        </div>

        {/* 에러 메시지 */}
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}

        {/* 버튼 */}
        <div className="flex gap-2 justify-end pt-1">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs text-theme-secondary hover:text-theme-primary bg-theme-tertiary rounded"
          >
            취소
          </button>
          <button
            onClick={handleSave}
            disabled={saving || saved}
            className="px-4 py-1.5 text-xs text-white bg-blue-600 hover:bg-blue-500 rounded disabled:opacity-50"
          >
            {saved ? "✓ 저장됨" : saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
