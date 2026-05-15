import { useEffect, useState } from "react";
import { getDashboard } from "../api";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-500">Error: {error}</p>;
  if (!data) return <p className="text-gray-400">Cargando...</p>;

  const stats = [
    { label: "Total consultas", value: data.total_queries, icon: "💬" },
    { label: "Usuarios", value: data.total_users, icon: "👥" },
    { label: "Documentos", value: `${data.indexed_documents}/${data.total_documents}`, icon: "📄" },
    { label: "Cultivos", value: data.total_crops, icon: "🌿" },
    { label: "Valoraciones", value: data.feedback.total_ratings, icon: "⭐" },
    { label: "Satisfacción", value: data.feedback.average_rating ? `${data.feedback.average_rating}/5` : "N/A", icon: "📊" },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Dashboard</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">{s.icon}</span>
              <span className="text-sm text-gray-500">{s.label}</span>
            </div>
            <p className="text-3xl font-bold text-gray-800">{s.value}</p>
          </div>
        ))}
      </div>

      {data.feedback.total_ratings > 0 && (
        <div className="mt-8 bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">Distribución de valoraciones</h3>
          <div className="flex items-end gap-4 h-32">
            {[1, 2, 3, 4, 5].map((star) => {
              const count = data.feedback.distribution[star] || 0;
              const max = Math.max(...Object.values(data.feedback.distribution), 1);
              const height = (count / max) * 100;
              return (
                <div key={star} className="flex flex-col items-center flex-1">
                  <div
                    className="w-full bg-green-500 rounded-t-md transition-all"
                    style={{ height: `${Math.max(height, 4)}%` }}
                  />
                  <span className="text-xs mt-2 text-gray-500">{"⭐".repeat(star)}</span>
                  <span className="text-xs text-gray-400">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}