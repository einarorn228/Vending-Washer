import React, { useEffect, useMemo, useState } from 'react';
import '../kiosk/styles/kiosk.css';
import './styles/dev-admin.css';
import DevAdminLockScreen from './DevAdminLockScreen.jsx';
import DevAdminShell, { TAB_IDS } from './DevAdminShell.jsx';
import { parseHelpHash } from './help/helpRouting.js';
import { HelpDrawerContext } from './help/HelpDrawerContext.js';
import HelpErrorBoundary from './help/HelpErrorBoundary.jsx';
import HelpPanel from './help/HelpPanel.jsx';
import HelpDrawer from './help/HelpDrawer.jsx';
import OverviewPanel from './components/OverviewPanel.jsx';
import SettingsPanel from './components/SettingsPanel.jsx';
import MachineCardsPanel from './components/MachineCardsPanel.jsx';
import RemoteControlPanel from './components/RemoteControlPanel.jsx';
import DiagnosticsPanel from './components/DiagnosticsPanel.jsx';
import {
  clearDevAdminKey,
  getDevAdminMachines,
  getDevAdminSettings,
  getDevAdminStatus,
  getStoredDevAdminKey,
} from './api.js';

const STATUS_REFRESH_MS = 5000;
const RESTART_PENDING_KEY = 'DEV_ADMIN_RESTART_PENDING';
const HELP_LOCALE_KEY = 'HELP_LOCALE';

function readHelpLocale() {
  if (typeof window === 'undefined') return 'is';
  try {
    return window.localStorage.getItem(HELP_LOCALE_KEY) || 'is';
  } catch {
    return 'is';
  }
}

function readHelpRoute() {
  if (typeof window === 'undefined') return { tab: 'overview', guideId: null, anchor: null, invalid: false };
  return parseHelpHash(window.location.hash, TAB_IDS);
}

function readRestartPending() {
  if (typeof window === 'undefined') return [];
  try {
    const stored = window.sessionStorage.getItem(RESTART_PENDING_KEY);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function DevAdminPage() {
  const [apiKey, setApiKey] = useState(getStoredDevAdminKey());
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [activeTab, setActiveTab] = useState(() => readHelpRoute().tab);
  // Task 15 consumes guideId/anchor/invalid to render a guide or the not-found state.
  const [helpRoute, setHelpRoute] = useState(readHelpRoute);
  const [helpLocale, setHelpLocale] = useState(readHelpLocale);
  // Drawer state is separate from helpRoute/the hash on purpose: the drawer is opened
  // by ContextualHelpLink from anywhere in the admin tree and must never disturb the
  // active tab or an in-progress edit underneath it.
  const [drawerGuide, setDrawerGuide] = useState(null); // {guideId, anchor, machineId} | null
  const [restartPending, setRestartPending] = useState(readRestartPending);
  const [status, setStatus] = useState(null);
  const [settingsGroups, setSettingsGroups] = useState([]);
  const [secretMetadata, setSecretMetadata] = useState({});
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [disabled, setDisabled] = useState(false);

  async function loadAll(key = apiKey) {
    if (!key) return;
    setLoading(true);
    setError('');
    setDisabled(false);
    const statusResult = await getDevAdminStatus(key);
    if (!statusResult.ok || !statusResult.payload?.success) {
      setLoading(false);
      if (statusResult.status === 403 || statusResult.payload?.disabled) {
        setDisabled(true);
        setError(statusResult.payload?.message || 'Beta dev/admin panel is disabled.');
      } else {
        clearDevAdminKey();
        setApiKey(null);
        setIsUnlocked(false);
        setError(statusResult.payload?.message || 'Session expired, or the admin username or password is invalid.');
      }
      return;
    }
    setStatus(statusResult.payload.status);
    setIsUnlocked(true);

    const [settingsResult, machinesResult] = await Promise.all([
      getDevAdminSettings(key),
      getDevAdminMachines(key),
    ]);
    if (settingsResult.ok && settingsResult.payload?.success) {
      const groups = settingsResult.payload.groups || [];
      setSettingsGroups(groups);
      
      const tokenSetting = groups.flatMap(g => g.settings || []).find(s => s.key === 'reisa_bearer_token');
      setSecretMetadata({ reisa_bearer_token_set: tokenSetting?.is_set });
    }
    if (machinesResult.ok && machinesResult.payload?.success) {
      setMachines(machinesResult.payload.machines || []);
    }
    setLoading(false);
  }

  const [recoveredKey, setRecoveredKey] = useState('');

  useEffect(() => {
    if (apiKey) {
      loadAll(apiKey);
    }
  }, []);

  // Overview reports live runtime facts (kiosk state, scanner availability), so it
  // has to keep refreshing rather than showing whatever was true at unlock time.
  useEffect(() => {
    if (!isUnlocked || !apiKey) return undefined;
    const interval = setInterval(async () => {
      const result = await getDevAdminStatus(apiKey);
      if (result.ok && result.payload?.success) {
        setStatus(result.payload.status);
      }
    }, STATUS_REFRESH_MS);
    return () => clearInterval(interval);
  }, [isUnlocked, apiKey]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const justGenerated = window.sessionStorage.getItem('JUST_GENERATED_API_KEY');
      if (justGenerated) {
        setRecoveredKey(justGenerated);
        window.sessionStorage.removeItem('JUST_GENERATED_API_KEY');
      }
    }
  }, []);

  // Keep the tab in the URL so a refresh (common on a kiosk tablet) stays put.
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const syncFromHash = () => {
      const route = readHelpRoute();
      setActiveTab(route.tab);
      setHelpRoute(route);
    };
    window.addEventListener('hashchange', syncFromHash);
    return () => window.removeEventListener('hashchange', syncFromHash);
  }, []);

  function handleTabChange(tab) {
    setActiveTab(tab);
    if (typeof window !== 'undefined') {
      window.location.hash = tab;
    }
  }

  function handleRestartRequired(labels) {
    setRestartPending((current) => {
      const merged = Array.from(new Set([...current, ...labels]));
      try {
        window.sessionStorage.setItem(RESTART_PENDING_KEY, JSON.stringify(merged));
      } catch {
        /* sessionStorage unavailable; the banner still shows for this session */
      }
      return merged;
    });
  }

  function handleDismissRestart() {
    setRestartPending([]);
    try {
      window.sessionStorage.removeItem(RESTART_PENDING_KEY);
    } catch {
      /* nothing to clean up */
    }
  }

  function handleHelpLocaleChange(nextLocale) {
    setHelpLocale(nextLocale);
    try {
      window.localStorage.setItem(HELP_LOCALE_KEY, nextLocale);
    } catch {
      /* localStorage unavailable; the preference just won't survive a reload */
    }
  }

  function openHelpDrawer(guideId, anchor, options = {}) {
    setDrawerGuide({ guideId, anchor: anchor || null, machineId: options.machineId || null });
  }

  function closeHelpDrawer() {
    setDrawerGuide(null);
  }

  // A related guide, guide_link, or checklist problem_guide clicked from inside the
  // drawer swaps its guide/anchor in place — it stays a drawer navigation, never the hash.
  function navigateHelpDrawer(guideId, anchor) {
    setDrawerGuide((current) => ({ guideId, anchor: anchor || null, machineId: current?.machineId || null }));
  }

  const helpDrawerContextValue = useMemo(() => ({ openHelpDrawer, locale: helpLocale }), [helpLocale]);

  function handleLockedOut() {
    setApiKey(null);
    setIsUnlocked(false);
    setStatus(null);
    setSettingsGroups([]);
    setMachines([]);
    setDisabled(true);
    setError('Beta dev/admin panel is now disabled. Re-enable it on the kiosk host to get back in.');
  }

  function handleUnlocked(key) {
    setApiKey(key);
    setIsUnlocked(true);
    loadAll(key);
  }

  function handleLock() {
    clearDevAdminKey();
    setApiKey(null);
    setIsUnlocked(false);
    setStatus(null);
    setSettingsGroups([]);
    setSecretMetadata({});
    setMachines([]);
  }

  if (!isUnlocked || !apiKey) {
    return <DevAdminLockScreen onUnlocked={handleUnlocked} />;
  }

  let content;
  if (activeTab === 'settings') {
    content = (
      <SettingsPanel
        apiKey={apiKey}
        groups={settingsGroups}
        secretMetadata={secretMetadata}
        onReload={() => loadAll(apiKey)}
        onLockedOut={handleLockedOut}
        onRestartRequired={handleRestartRequired}
      />
    );
  } else if (activeTab === 'machines') {
    content = <MachineCardsPanel apiKey={apiKey} machines={machines} onReload={() => loadAll(apiKey)} />;
  } else if (activeTab === 'remote_control') {
    content = <RemoteControlPanel apiKey={apiKey} />;
  } else if (activeTab === 'diagnostics') {
    content = <DiagnosticsPanel apiKey={apiKey} />;
  } else if (activeTab === 'help') {
    content = (
      <HelpErrorBoundary locale={helpLocale} resetKey={`${helpRoute.guideId}:${helpRoute.anchor}:${helpLocale}`}>
        <HelpPanel apiKey={apiKey} helpRoute={helpRoute} locale={helpLocale} onLocaleChange={handleHelpLocaleChange} />
      </HelpErrorBoundary>
    );
  } else {
    content = <OverviewPanel apiKey={apiKey} status={status} onReload={() => loadAll(apiKey)} />;
  }

  return (
    <HelpDrawerContext.Provider value={helpDrawerContextValue}>
      <DevAdminShell
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onLock={handleLock}
        restartPending={restartPending}
        onDismissRestart={handleDismissRestart}
      >
        {loading ? <div className="dev-admin-loading">Loading beta dev/admin data…</div> : null}
        {disabled ? <div className="dev-admin-disabled">{error}</div> : error ? <div className="dev-admin-form-error">{error}</div> : null}

        {recoveredKey && (
          <div className="dev-admin-modal-overlay" style={{ zIndex: 9999 }}>
            <div className="dev-admin-modal dev-admin-modal--important">
              <h3>New API Key Generated</h3>
              <p>Here is your new API token for the application. <strong>Please ensure you write it down before closing this window.</strong> It will not be shown again.</p>
              <div className="dev-admin-code-block">
                <code>{recoveredKey}</code>
              </div>
              <button className="dev-admin-primary" onClick={() => setRecoveredKey('')}>I have written it down</button>
            </div>
          </div>
        )}

        {content}

        {drawerGuide ? (
          <HelpErrorBoundary locale={helpLocale} resetKey={`${drawerGuide.guideId}:${drawerGuide.anchor}:${helpLocale}`}>
            <HelpDrawer
              guideId={drawerGuide.guideId}
              anchor={drawerGuide.anchor}
              machineId={drawerGuide.machineId}
              apiKey={apiKey}
              locale={helpLocale}
              onClose={closeHelpDrawer}
              onNavigate={navigateHelpDrawer}
            />
          </HelpErrorBoundary>
        ) : null}
      </DevAdminShell>
    </HelpDrawerContext.Provider>
  );
}
