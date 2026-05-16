import { useEffect, useState } from "react";
import { getAnalytics, getEvalDataset } from "../api";
import { useLang } from "../context/LangContext";

export default function Analytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [evalData, setEvalData] = useState(null);
  const [exportingEval, setExportingEval] = useState(false);
  const { t } = useLang();

  useEffect(() => {
    getAnalytics().then(setData).catch((e) => setError(e.message));
  }, []);

  const handleExportEval = async () => {
    setExportingEval(true);
    try {
      const result = await getEvalDataset();
      setEvalData(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setExportingEval(false);
    }
  };

  const handleDownloadJson = () => {
    if (!evalData) return;
    const blob = new Blob([JSON.stringify(evalData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "eval_dataset_from_feedback.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) return <p className="text-red-500">{t("error")}: {error}</p>;
  if (!data) return <p className="text-gray-400">{t("loading")}</p>;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">{t("analytics_title")}</h2>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">{t("analytics_by_crop")}</h3>
        {data.crop_metrics.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">{t("analytics_crop")}</th>
                <th className="text-center px-4 py-3 text-gray-500 font-medium">{t("analytics_queries")}</th>
                <th className="text-center px-4 py-3 text-gray-500 font-medium">{t("analytics_satisfaction")}</th>
                <th className="text-center px-4 py-3 text-gray-500 font-medium">{t("analytics_avg_time")}</th>
              </tr>
            </thead>
            <tbody>
              {data.crop_metrics.map((crop) => (
                <tr key={crop.crop} className="border-b border-gray-100">
                  <td className="px-4 py-3 font-medium">{crop.crop}</td>
                  <td className="px-4 py-3 text-center">{crop.queries}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`font-medium ${crop.avg_rating >= 4 ? "text-green-600" : crop.avg_rating >= 3 ? "text-yellow-600" : "text-red-600"}`}>
                      {crop.avg_rating}/5
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-500">{crop.avg_time}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-400 text-sm">{t("analytics_no_data")}</p>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-4">{t("analytics_lang_dist")}</h3>
        <div className="flex gap-4">
          {Object.entries(data.lang_distribution).map(([lang, count]) => (
            <div key={lang} className="bg-gray-50 rounded-lg px-4 py-3 text-center">
              <p className="text-2xl font-bold text-gray-800">{count}</p>
              <p className="text-xs text-gray-500 mt-1">{lang.toUpperCase()}</p>
            </div>
          ))}
          {Object.keys(data.lang_distribution).length === 0 && (
            <p className="text-gray-400 text-sm">{t("analytics_no_data")}</p>
          )}
        </div>
      </div>

      {data.daily_trend.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">{t("analytics_daily_trend")}</h3>
          <div className="flex items-end gap-1 h-32">
            {data.daily_trend.map((day) => {
              const max = Math.max(...data.daily_trend.map((d) => d.queries), 1);
              const height = (day.queries / max) * 100;
              return (
                <div key={day.date} className="flex flex-col items-center flex-1" title={`${day.date}: ${day.queries}`}>
                  <div
                    className="w-full bg-green-500 rounded-t-sm transition-all"
                    style={{ height: `${Math.max(height, 4)}%` }}
                  />
                  <span className="text-xs text-gray-400 mt-1 rotate-45 origin-left whitespace-nowrap">
                    {day.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data.low_rated.length > 0 && (
        <div className="bg-white rounded-xl border border-red-200 p-5 mb-6">
          <h3 className="text-lg font-semibold text-red-700 mb-4">{t("analytics_low_rated")}</h3>
          <div className="flex flex-col gap-3">
            {data.low_rated.map((item, i) => (
              <div key={i} className="border border-red-100 rounded-lg p-3">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                    {"⭐".repeat(item.rating)}
                  </span>
                  <span className="text-xs text-gray-400">{item.lang}</span>
                </div>
                <p className="font-medium text-gray-800 text-sm">{item.question}</p>
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.answer}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h3 className="text-lg font-semibold text-gray-700 mb-2">{t("analytics_eval_title")}</h3>
        <p className="text-sm text-gray-500 mb-4">{t("analytics_eval_desc")}</p>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportEval}
            disabled={exportingEval}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {exportingEval ? t("analytics_eval_generating") : t("analytics_eval_generate")}
          </button>
          {evalData && (
            <button
              onClick={handleDownloadJson}
              className="bg-gray-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-700"
            >
              {t("analytics_eval_download")}
            </button>
          )}
        </div>
        {evalData && (
          <div className="mt-4 flex gap-4">
            <div className="bg-green-50 rounded-lg px-4 py-3 text-center">
              <p className="text-2xl font-bold text-green-700">{evalData.good_responses.count}</p>
              <p className="text-xs text-green-600">{t("analytics_eval_good")}</p>
            </div>
            <div className="bg-red-50 rounded-lg px-4 py-3 text-center">
              <p className="text-2xl font-bold text-red-700">{evalData.bad_responses.count}</p>
              <p className="text-xs text-red-600">{t("analytics_eval_bad")}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}