const STORAGE_KEY = 'API_KEY';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

function getApiKey() {
  const envKey = import.meta.env.VITE_API_KEY;
  if (envKey) return envKey;

  if (typeof window !== 'undefined') {
    const storedKey = window.localStorage.getItem(STORAGE_KEY);
    if (storedKey) return storedKey;
  }

  console.warn('No API key configured. Set VITE_API_KEY or localStorage API_KEY.');
  return null;
}

async function request(path, options = {}) {
  const apiKey = getApiKey();
  if (!apiKey) {
    return null;
  }

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
    'X-API-KEY': apiKey,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (options.allowErrorPayload) {
        return {
          ok: false,
          status: response.status,
          payload,
        };
      }

      console.error('Request failed', response.status, payload);
      return null;
    }

    if (options.allowErrorPayload) {
      return {
        ok: true,
        status: response.status,
        payload,
      };
    }

    return payload;
  } catch (error) {
    console.error('Request failed', error);
    return null;
  }
}

export function pollState() {
  return request('/api/ui_state');
}

export async function touchSelectMachine(machineId) {
  if (typeof machineId !== 'string' || !machineId.trim()) {
    return {
      success: false,
      message: 'Invalid machine selection.',
      state: null,
      uses_left: null,
    };
  }

  const result = await request('/api/touch_select_machine', {
    method: 'POST',
    body: JSON.stringify({ machine_id: machineId }),
    allowErrorPayload: true,
  });

  if (!result) {
    return {
      success: false,
      message: 'Unable to reach backend right now.',
      state: null,
      uses_left: null,
    };
  }

  const payload = result.payload && typeof result.payload === 'object' ? result.payload : {};

  return {
    success: Boolean(payload.success && result.ok),
    message: typeof payload.message === 'string' ? payload.message : 'Machine selection failed.',
    state: typeof payload.state === 'string' ? payload.state : null,
    uses_left: typeof payload.uses_left === 'number' ? payload.uses_left : null,
    status: result.status,
  };
}
