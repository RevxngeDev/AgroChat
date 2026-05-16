import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearApiKey } from "../api";
import { useLang } from "../context/LangContext";

const LANG_OPTIONS = [
  { code: "es", label: "ES" },
  { code: "en", label: "EN" },
  { code: "ru", label: "RU" },
];

export default function Layout() {
  const navigate = useNavigate();
  const { t, lang, changeLang } = useLang();

  const navItems = [
    { to: "/", label: t("sidebar_dashboard"), icon: "📊" },
    { to: "/documents", label: t("sidebar_documents"), icon: "📄" },
    { to: "/query-logs", label: t("sidebar_queries"), icon: "💬" },
    { to: "/feedback", label: t("sidebar_feedback"), icon: "⭐" },
    { to: "/analytics", label: t("sidebar_analytics"), icon: "📈" },
  ];

  const handleLogout = () => {
    clearApiKey();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-200 p-4 flex flex-col">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-green-700">🌱 {t("sidebar_title")}</h1>
          <p className="text-xs text-gray-400 mt-1">{t("sidebar_subtitle")}</p>
        </div>

        <div className="flex gap-1 mb-6">
          {LANG_OPTIONS.map((opt) => (
            <button
              key={opt.code}
              onClick={() => changeLang(opt.code)}
              className={`px-2 py-1 rounded text-xs font-medium transition ${
                lang === opt.code
                  ? "bg-green-100 text-green-700"
                  : "text-gray-400 hover:bg-gray-100"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <nav className="flex flex-col gap-1 flex-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${
                  isActive
                    ? "bg-green-50 text-green-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100"
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-red-500 hover:bg-red-50 transition mt-auto"
        >
          <span>🚪</span>
          {t("sidebar_logout")}
        </button>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}