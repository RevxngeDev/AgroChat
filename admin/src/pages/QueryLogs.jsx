import { useEffect, useState } from "react";
import { getQueryLogs } from "../api";

export default function QueryLogs() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getQueryLogs()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-500">Error: {error}</p>;
  if (!data) return <p className="text-gray-400">Cargando...</p>;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-2">Consultas</h2>
      <p className="text-gray-500 text-sm mb-6">Total: {data.total}</p>

      <div className="flex flex-col gap-3">
        {data.data.map((log) => (
          <div key={log.id} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                {log.lang || "es"}
              </span>
              <span className="text-xs text-gray-400">
                {new Date(log.created_at).toLocaleString()}
              </span>
            </div>
            <p className="font-medium text-gray-800 mb-1">
              {log.question}
            </p>
            <p className="text-sm text-gray-500 line-clamp-2">
              {log.answer}
            </p>
            <div className="flex gap-4 mt-2 text-xs text-gray-400">
              <span>Modelo: {log.model}</span>
              <span>Chunks: {log.chunks_found}</span>
              <span>Tiempo: {log.elapsed_sec}s</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}