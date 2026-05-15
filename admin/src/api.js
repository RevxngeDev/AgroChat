const API_URL = "http://localhost:8000";
const API_KEY = "agrochat-admin-2026";

async function request(endpoint) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: { "x-api-key": API_KEY },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getDashboard() {
  return request("/admin/dashboard");
}

export async function getQueryLogs(limit = 50, offset = 0) {
  return request(`/admin/query-logs?limit=${limit}&offset=${offset}`);
}

export async function getFeedback(limit = 50) {
  return request(`/admin/feedback?limit=${limit}`);
}

export async function getDocuments() {
  return request("/admin/documents");
}

export async function uploadDocument(crop, file) {
  const formData = new FormData();
  formData.append("crop", crop);
  formData.append("file", file);

  const res = await fetch(`${API_URL}/admin/documents/upload`, {
    method: "POST",
    headers: { "x-api-key": API_KEY },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function triggerReindex() {
  const res = await fetch(`${API_URL}/admin/reindex`, {
    method: "POST",
    headers: { "x-api-key": API_KEY },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Reindex failed");
  }
  return res.json();
}