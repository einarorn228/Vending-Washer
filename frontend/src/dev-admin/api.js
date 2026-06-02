const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const DEV_ADMIN_KEY = 'DEV_ADMIN_AUTH';

export function getStoredDevAdminKey() {
  if (typeof window === 'undefined') return null;
  const value = window.sessionStorage.getItem(DEV_ADMIN_KEY);
  return value && value.trim() ? value.trim() : null;
}

export function storeDevAdminKey(username, password) {
  if (typeof window !== 'undefined') {
    const b64 = btoa(`${username}:${password}`);
    window.sessionStorage.setItem(DEV_ADMIN_KEY, b64);
  }
}

export function clearDevAdminKey() {
  if (typeof window !== 'undefined') {
    window.sessionStorage.removeItem(DEV_ADMIN_KEY);
  }
}

async function devAdminRequest(path, apiKey, options = {}) {
  if (!apiKey) {
    return { ok: false, status: 401, payload: { success: false, message: 'Missing API key.' } };
  }

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
    'Authorization': `Basic ${apiKey}`,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/dev_admin${path}`, {
      ...options,
      headers,
      cache: 'no-store',
    });
    const payload = await response.json().catch(() => ({}));
    return { ok: response.ok, status: response.status, payload };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      payload: { success: false, message: error?.message || 'Unable to reach backend.' },
    };
  }
}

export function unlockDevAdmin(apiKey) {
  return devAdminRequest('/unlock', apiKey, { method: 'POST', body: JSON.stringify({}) });
}

export function getDevAdminStatus(apiKey) {
  return devAdminRequest('/status', apiKey);
}

export function getDevAdminSettings(apiKey) {
  return devAdminRequest('/settings', apiKey);
}

export function saveDevAdminSettings(apiKey, changes, currentApiKey = null) {
  const body = { changes };
  if (currentApiKey) {
    body.current_api_key = currentApiKey;
  }
  return devAdminRequest('/settings', apiKey, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function generateNewApiKey(authKey, currentApiKey) {
  return devAdminRequest('/generate_api_key', authKey, {
    method: 'POST',
    body: JSON.stringify({ current_api_key: currentApiKey }),
  });
}

export function getDevAdminMachines(apiKey) {
  return devAdminRequest('/machines', apiKey);
}

export function saveDevAdminMachine(apiKey, machineKey, changes) {
  return devAdminRequest(`/machines/${encodeURIComponent(machineKey)}`, apiKey, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  });
}

export function saveMachineOrder(apiKey, order) {
  return devAdminRequest('/machine-layout', apiKey, {
    method: 'PATCH',
    body: JSON.stringify({ order }),
  });
}

export function exportDevAdminConfig(apiKey) {
  return devAdminRequest('/export-config', apiKey);
}
