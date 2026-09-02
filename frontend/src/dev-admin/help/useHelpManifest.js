// frontend/src/dev-admin/help/useHelpManifest.js
//
// Fetches the compiled Help manifest once per apiKey and caches it at module
// scope (not per-hook-instance) so the Help tab and the drawer — which mounts
// and unmounts independently every time a ContextualHelpLink is clicked —
// share one cached result and, while a fetch is in flight, one shared request
// instead of each issuing its own GET /help/manifest. Never throws:
// GET /help/manifest degrades in three ways — 200 (manifest present), 503
// (compiled manifest missing/broken, a reason code only), or any other
// non-ok status (a plain message) — and all three are folded into
// {manifest, status, error, loading} for the caller.

import { useEffect, useState } from 'react';
import { getHelpManifest } from '../api.js';

// Keyed by apiKey. A value is either the resolved {manifest, status, error}
// or, while the fetch is still in flight, the pending Promise for it — so a
// second mount that arrives before the first fetch resolves awaits the same
// request rather than starting a new one. A failed fetch (error is truthy)
// is never cached as a settled result: the entry is cleared so a later mount
// (e.g. reopening the drawer) gets a real retry instead of being stuck on
// the same failure forever.
const manifestCache = new Map();

function fetchAndCache(apiKey) {
  const pending = getHelpManifest(apiKey)
    .then((result) => {
      let manifest = null;
      let status = null;
      let error = '';

      if (result.ok && result.payload?.success) {
        manifest = result.payload.manifest ?? null;
        status = result.payload.status ?? null;
      } else if (result.status === 503) {
        error = result.payload?.reason || 'unavailable';
      } else {
        error = result.payload?.message || 'Could not load the help manifest.';
      }

      const resolved = { manifest, status, error };
      if (error) {
        manifestCache.delete(apiKey);
      } else {
        manifestCache.set(apiKey, resolved);
      }
      return resolved;
    })
    .catch(() => {
      const resolved = { manifest: null, status: null, error: 'Could not load the help manifest.' };
      manifestCache.delete(apiKey);
      return resolved;
    });

  manifestCache.set(apiKey, pending);
  return pending;
}

export function useHelpManifest(apiKey) {
  const [manifest, setManifest] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!apiKey) {
      setManifest(null);
      setStatus(null);
      setError('');
      setLoading(false);
      return undefined;
    }

    let cancelled = false;
    const cached = manifestCache.get(apiKey);

    if (cached && !(cached instanceof Promise)) {
      setManifest(cached.manifest);
      setStatus(cached.status);
      setError(cached.error);
      setLoading(false);
      return undefined;
    }

    setLoading(true);
    const pending = cached instanceof Promise ? cached : fetchAndCache(apiKey);

    pending.then((resolved) => {
      if (cancelled) return;
      setManifest(resolved.manifest);
      setStatus(resolved.status);
      setError(resolved.error);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  return { manifest, status, error, loading };
}
