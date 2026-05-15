import { useEffect, useState } from "react";
import { getFeedback } from "../api";

export default function Feedback() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getFeedback()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-500">Error: {error}</p>;
  if (!data) return <p className="text-gray-400">Cargando...</p>;

  const { stats, data: entries } = data;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Feedback</h2>
      <p className="text-gray-500 text-sm mb-6">
        {stats.total_ratings} valoraciones · Promedio: {stats.average_rating || "N/A"}/5
      </p>

      <div className="flex flex-col gap-3">
        {entries.map((entry) => (
          <div key={entry.id} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex justify-between items-start mb-2">
              <span className="text-lg">
                {"⭐".repeat(entry.rating)}{"☆".repeat(5 - entry.rating)}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(entry.created_at).toLocaleString()}
              </span>
            </div>
            {entry.query_logs && (
              <>
                <p className="font-medium text-gray-800 text-sm mb-1">
                  {entry.query_logs.question}
                </p>
                <p className="text-sm text-gray-500 line-clamp-2">
                  {entry.query_logs.answer}
                </p>
              </>
            )}
          </div>
        ))}

        {entries.length === 0 && (
          <p className="text-gray-400 text-sm">No hay valoraciones aún.</p>
        )}
      </div>
    </div>
  );
}