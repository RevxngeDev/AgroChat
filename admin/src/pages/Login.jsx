import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { validateLogin, setApiKey } from "../api";
import { useLang } from "../context/LangContext";

const LANG_OPTIONS = [
  { code: "es", label: "ES" },
  { code: "en", label: "EN" },
  { code: "ru", label: "RU" },
];

export default function Login() {
  const [key, setKey] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { t, lang, changeLang } = useLang();

  const handleLogin = async () => {
    if (!key.trim()) return;
    setLoading(true);
    setError(false);
    try {
      await validateLogin(key.trim());
      setApiKey(key.trim());
      navigate("/");
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleLogin();
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 w-full max-w-sm">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-green-700">🌱 AgroChat</h1>
          <p className="text-sm text-gray-400 mt-1">{t("login_title")}</p>
        </div>

        <div className="flex justify-center gap-1 mb-6">
          {LANG_OPTIONS.map((opt) => (
            <button
              key={opt.code}
              onClick={() => changeLang(opt.code)}
              className={`px-3 py-1 rounded text-xs font-medium transition ${
                lang === opt.code
                  ? "bg-green-100 text-green-700"
                  : "text-gray-400 hover:bg-gray-100"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t("login_label")}
            </label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("login_placeholder")}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              autoFocus
            />
          </div>
          {error && <p className="text-sm text-red-500">{t("login_error")}</p>}
          <button
            onClick={handleLogin}
            disabled={loading || !key.trim()}
            className="w-full bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t("login_verifying") : t("login_button")}
          </button>
        </div>
      </div>
    </div>
  );
}