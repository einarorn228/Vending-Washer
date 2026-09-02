// frontend/src/dev-admin/help/useHelpManifest.js
//
// Fetches the compiled Help manifest once per apiKey and caches it in a ref
// so remounting the Help tab (switching panels, reopening the drawer) does
// not re-fetch. Never throws: GET /help/manifest degrades in three ways —
// 200 (manifest present), 503 (compiled manifest missing/broken, a reason
// code only), or any other non-ok status (a plain message) — and all three
// are folded into {manifest, status, error, loading} for the caller.

import { useEffect, useRef, useState } from 'react';
import { getHelpManifest } from '../api.js';

export function useHelpManifest(apiKey) {
  const [manifest, setManifest] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const cacheRef = useRef({});

  useEffect(() => {
    if (!apiKey) {
      setManifest(null);
      setStatus(null);
      setError('');
      setLoading(false);
      return undefined;
    }

    const cached = cacheRef.current[apiKey];
    if (cached) {
      setManifest(cached.manifest);
      setStatus(cached.status);
      setError(cached.error);
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    setLoading(true);

    async function fetchManifest() {
      const result = await getHelpManifest(apiKey);
      if (cancelled) return;

      let nextManifest = null;
      let nextStatus = null;
      let nextError = '';

      if (result.ok && result.payload?.success) {
        nextManifest = result.payload.manifest ?? null;
        nextStatus = result.payload.status ?? null;
      } else if (result.status === 503) {
        nextError = result.payload?.reason || 'unavailable';
      } else {
        nextError = result.payload?.message || 'Could not load the help manifest.';
      }

      cacheRef.current[apiKey] = { manifest: nextManifest, status: nextStatus, error: nextError };
      setManifest(nextManifest);
      setStatus(nextStatus);
      setError(nextError);
      setLoading(false);
    }

    fetchManifest();
    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  return { manifest, status, error, loading };
}
