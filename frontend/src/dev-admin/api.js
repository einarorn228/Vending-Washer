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

export function saveDevAdminSettings(apiKey, changes, currentApiKey = null, confirmationPhrase = null) {
  const body = { changes };
  if (currentApiKey) {
    body.current_api_key = currentApiKey;
  }
  if (confirmationPhrase) {
    body.confirmation_phrase = confirmationPhrase;
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

// One transaction for the whole card panel: either every changed machine and the
// display order are saved, or nothing is.
export function saveDevAdminMachines(apiKey, updates, order = null) {
  const body = { updates };
  if (order) {
    body.order = order;
  }
  return devAdminRequest('/machines', apiKey, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

export function exportDevAdminConfig(apiKey) {
  return devAdminRequest('/export-config', apiKey);
}

export function getKioskState(apiKey) {
  return devAdminRequest('/kiosk_state', apiKey);
}

export function remoteScan(apiKey, code) {
  return devAdminRequest('/remote_scan', apiKey, {
    method: 'POST',
    body: JSON.stringify({ code }),
  });
}

export function remoteTouchSelect(apiKey, machineId) {
  return devAdminRequest('/remote_touch_select', apiKey, {
    method: 'POST',
    body: JSON.stringify({ machine_id: machineId }),
  });
}

export function getDevAdminTelemetry(apiKey) {
  return devAdminRequest('/telemetry', apiKey);
}

export function getDevAdminDiagnostics(apiKey, limit = 50) {
  return devAdminRequest(`/diagnostics?limit=${encodeURIComponent(limit)}`, apiKey);
}

export function remoteReset(apiKey) {
  return devAdminRequest('/remote_reset', apiKey, { method: 'POST', body: JSON.stringify({}) });
}

export function getHelpManifest(apiKey) {
  return devAdminRequest('/help/manifest', apiKey);
}
