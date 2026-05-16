import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearApiKey } from "../api";

const navItems = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/documents", label: "Documentos", icon: "📄" },
  { to: "/query-logs", label: "Consultas", icon: "💬" },
  { to: "/feedback", label: "Feedback", icon: "⭐" },
  { to: "/analytics", label: "Analytics", icon: "📈" },
];

export default function Layout() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearApiKey();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-200 p-4 flex flex-col">
        <div className="mb-8">
          <h1 className="text-xl font-bold text-green-700">🌱 AgroChat</h1>
          <p className="text-xs text-gray-400 mt-1">Admin Panel</p>
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
          Cerrar sesión
        </button>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}