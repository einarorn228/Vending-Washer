import React, { useEffect, useState } from 'react';
import '../kiosk/styles/kiosk.css';
import './styles/dev-admin.css';
import DevAdminLockScreen from './DevAdminLockScreen.jsx';
import DevAdminShell from './DevAdminShell.jsx';
import OverviewPanel from './components/OverviewPanel.jsx';
import SettingsPanel from './components/SettingsPanel.jsx';
import MachineCardsPanel from './components/MachineCardsPanel.jsx';
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
      setSettingsGroups(settingsResult.payload.groups || []);
    }
    if (machinesResult.ok && machinesResult.payload?.success) {
      setMachines(machinesResult.payload.machines || []);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (apiKey) {
      loadAll(apiKey);
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
    setMachines([]);
  }

  if (!isUnlocked || !apiKey) {
    return <DevAdminLockScreen onUnlocked={handleUnlocked} />;
  }

  let content;
  if (activeTab === 'settings') {
    content = <SettingsPanel apiKey={apiKey} groups={settingsGroups} onReload={() => loadAll(apiKey)} />;
  } else if (activeTab === 'machines') {
    content = <MachineCardsPanel apiKey={apiKey} machines={machines} onReload={() => loadAll(apiKey)} />;
  } else {
    content = <OverviewPanel apiKey={apiKey} status={status} onReload={() => loadAll(apiKey)} />;
  }

  return (
    <DevAdminShell activeTab={activeTab} onTabChange={setActiveTab} onLock={handleLock}>
      {loading ? <div className="dev-admin-loading">Loading beta dev/admin data…</div> : null}
      {disabled ? <div className="dev-admin-disabled">{error}</div> : error ? <div className="dev-admin-form-error">{error}</div> : null}
      {content}
    </DevAdminShell>
  );
}
