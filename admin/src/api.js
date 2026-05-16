const API_URL = "http://localhost:8000";

function getApiKey() {
  return sessionStorage.getItem("admin_api_key") || "";
}

export function setApiKey(key) {
  sessionStorage.setItem("admin_api_key", key);
}

export function clearApiKey() {
  sessionStorage.removeItem("admin_api_key");
}

export function isAuthenticated() {
  return !!sessionStorage.getItem("admin_api_key");
}

async function request(endpoint) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: { "x-api-key": getApiKey() },
  });
  if (res.status === 401) {
    clearApiKey();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function validateLogin(key) {
  const res = await fetch(`${API_URL}/admin/dashboard`, {
    headers: { "x-api-key": key },
  });
  if (res.status === 401) throw new Error("Invalid API key");
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return true;
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
    headers: { "x-api-key": getApiKey() },
    body: formData,
  });
  if (res.status === 401) {
    clearApiKey();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function triggerReindex() {
  const res = await fetch(`${API_URL}/admin/reindex`, {
    method: "POST",
    headers: { "x-api-key": getApiKey() },
  });
  if (res.status === 401) {
    clearApiKey();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Reindex failed");
  }
  return res.json();
}

export async function createCrop(name, label) {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("label", label);

  const res = await fetch(`${API_URL}/admin/crops`, {
    method: "POST",
    headers: { "x-api-key": getApiKey() },
    body: formData,
  });
  if (res.status === 401) {
    clearApiKey();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create crop");
  }
  return res.json();
}

export async function getAnalytics() {
  return request("/admin/analytics");
}

export async function getEvalDataset() {
  return request("/admin/analytics/eval-dataset");
}