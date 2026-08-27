import React, { useEffect, useState } from 'react';
import '../kiosk/styles/kiosk.css';
import './styles/dev-admin.css';
import DevAdminLockScreen from './DevAdminLockScreen.jsx';
import DevAdminShell from './DevAdminShell.jsx';
import OverviewPanel from './components/OverviewPanel.jsx';
import SettingsPanel from './components/SettingsPanel.jsx';
import MachineCardsPanel from './components/MachineCardsPanel.jsx';
import RemoteControlPanel from './components/RemoteControlPanel.jsx';
import {
  clearDevAdminKey,
  getDevAdminMachines,
  getDevAdminSettings,
  getDevAdminStatus,
  getStoredDevAdminKey,
} from './api.js';

export default function DevAdminPage() {
  const [apiKey, setApiKey] = useState(getStoredDevAdminKey());
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
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
        setError(statusResult.payload?.message || 'Unlock expired or API key is invalid.');
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

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const justGenerated = window.sessionStorage.getItem('JUST_GENERATED_API_KEY');
      if (justGenerated) {
        setRecoveredKey(justGenerated);
        window.sessionStorage.removeItem('JUST_GENERATED_API_KEY');
      }
    }
  }, []);

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
    content = <SettingsPanel apiKey={apiKey} groups={settingsGroups} secretMetadata={secretMetadata} onReload={() => loadAll(apiKey)} />;
  } else if (activeTab === 'machines') {
    content = <MachineCardsPanel apiKey={apiKey} machines={machines} onReload={() => loadAll(apiKey)} />;
  } else if (activeTab === 'remote_control') {
    content = <RemoteControlPanel apiKey={apiKey} />;
  } else {
    content = <OverviewPanel apiKey={apiKey} status={status} onReload={() => loadAll(apiKey)} />;
  }

  return (
    <DevAdminShell activeTab={activeTab} onTabChange={setActiveTab} onLock={handleLock}>
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
    </DevAdminShell>
  );
}
