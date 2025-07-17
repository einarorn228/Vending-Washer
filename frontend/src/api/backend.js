const API_KEY = localStorage.getItem("API_KEY") || ""; // set via config

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", "X-API-KEY": API_KEY };
  try {
    const res = await fetch(path, { ...options, headers });
    return await res.json();
  } catch (e) {
    console.error("Request failed", e);
    return null;
  }
}

export function pollState() {
  return request("/api/ui_state");
}
