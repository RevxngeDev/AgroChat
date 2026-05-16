import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { validateLogin, setApiKey } from "../api";

export default function Login() {
  const [key, setKey] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!key.trim()) return;
    setLoading(true);
    setError(null);

    try {
      await validateLogin(key.trim());
      setApiKey(key.trim());
      navigate("/");
    } catch (e) {
      setError("Clave inválida. Intenta de nuevo.");
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
          <p className="text-sm text-gray-400 mt-1">Admin Panel</p>
        </div>

        <div className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Admin API Key
            </label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ingresa la clave de administrador"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
              autoFocus
            />
          </div>

          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          <button
            onClick={handleLogin}
            disabled={loading || !key.trim()}
            className="w-full bg-green-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Verificando..." : "Ingresar"}
          </button>
        </div>
      </div>
    </div>
  );
}