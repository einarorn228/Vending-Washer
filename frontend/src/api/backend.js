const STORAGE_KEY = "API_KEY";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function getApiKey() {
  const envKey = import.meta.env.VITE_API_KEY;
  if (envKey && String(envKey).trim()) return String(envKey).trim();

  if (typeof window !== "undefined") {
    const storedKey = window.localStorage.getItem(STORAGE_KEY);
    if (storedKey && String(storedKey).trim()) return String(storedKey).trim();
  }

  console.warn("No API key configured. Set VITE_API_KEY or localStorage API_KEY.");
  return null;
}

/** True if the UI can attach X-API-KEY (env at Vite start, or localStorage). */
export function isApiKeyConfigured() {
  return getApiKey() != null;
}


async function request(path, options = {}) {
  const apiKey = getApiKey();
  if (!apiKey) {
    return null;
  }

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    "X-API-KEY": apiKey,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      console.error("Request failed", response.status, errorPayload);
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error("Request failed", error);
    return null;
  }
}

export function pollState() {
  return request("/api/ui_state");
}
