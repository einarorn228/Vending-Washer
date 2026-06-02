import React, { useState } from 'react';
import { saveDevAdminSettings, generateNewApiKey } from '../api.js';

export default function SecuritySettingsPanel({ authKey, reisaTokenIsSet }) {
  const [currentApiKey, setCurrentApiKey] = useState('');
  const [newReisaToken, setNewReisaToken] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [generatedKey, setGeneratedKey] = useState('');

  async function handleUpdateReisaToken(e) {
    e.preventDefault();
    if (!currentApiKey) {
      setError('Current API key is required to update sensitive settings.');
      return;
    }
    if (!newReisaToken.trim()) {
      setError('New Reisa token cannot be empty.');
      return;
    }
    
    setSaving(true);
    setMessage('');
    setError('');
    const result = await saveDevAdminSettings(authKey, { reisa_bearer_token: newReisaToken.trim() }, currentApiKey);
    setSaving(false);
    
    if (!result.ok || !result.payload?.success) {
      setError(result.payload?.message || 'Failed to update Reisa token.');
    } else {
      setMessage('Reisa token successfully updated.');
      setNewReisaToken('');
    }
  }

  async function handleGenerateApiKey() {
    if (!currentApiKey) {
      setError('Current API key is required to generate a new API key.');
      return;
    }
    
    if (!window.confirm('Are you sure you want to generate a new API key? All kiosks using the old key will lose access.')) {
      return;
    }

    setSaving(true);
    setMessage('');
    setError('');
    setGeneratedKey('');
    
    const result = await generateNewApiKey(authKey, currentApiKey);
    setSaving(false);
    
    if (!result.ok || !result.payload?.success) {
      setError(result.payload?.message || 'Failed to generate new API key.');
    } else {
      setGeneratedKey(result.payload.new_api_key);
    }
  }

  return (
    <section className="dev-admin-panel">
      <div className="dev-admin-panel__header">
        <div>
          <p className="dev-admin-eyebrow">Security</p>
          <h2>Sensitive Settings</h2>
        </div>
      </div>
      <div className="dev-admin-warning">
        These settings are highly sensitive. To modify them, you MUST provide the current active API key.
      </div>
      
      {generatedKey && (
        <div className="dev-admin-modal-overlay">
          <div className="dev-admin-modal dev-admin-modal--important">
            <h3>New API Key Generated</h3>
            <p>Here is your new API token for the application. <strong>Please ensure you write it down before closing this window.</strong> It will not be shown again.</p>
            <div className="dev-admin-code-block">
              <code>{generatedKey}</code>
            </div>
            <button className="dev-admin-primary" onClick={() => setGeneratedKey('')}>I have written it down</button>
          </div>
        </div>
      )}

      <article className="dev-admin-group-card">
        <h3>Current Verification Key</h3>
        <p className="dev-admin-eyebrow" style={{ marginBottom: '1rem', textTransform: 'none' }}>
          You must enter the <strong>Current API Key</strong> below to authorize any changes in this section.
        </p>
        <div className="dev-admin-setting">
          <div className="dev-admin-setting__meta">
            <label>Current API Key</label>
            <p>Required to verify your identity before rotating keys.</p>
          </div>
          <div className="dev-admin-setting__control">
            <input 
              type="password" 
              placeholder="Enter current API key..."
              value={currentApiKey} 
              onChange={e => setCurrentApiKey(e.target.value)} 
            />
          </div>
        </div>

        <h3>Reisa Provider Integration</h3>
        <form onSubmit={handleUpdateReisaToken} className="dev-admin-setting">
          <div className="dev-admin-setting__meta">
            <label>Update Reisa Token</label>
            <p>Current status: <span className="dev-admin-secret">{reisaTokenIsSet ? 'Set / masked' : 'Not set'}</span></p>
            <p>Change the Bearer token used for Reisa integration.</p>
          </div>
          <div className="dev-admin-setting__control">
            <input 
              type="password" 
              placeholder="Enter new token..." 
              value={newReisaToken} 
              onChange={e => setNewReisaToken(e.target.value)} 
            />
            <button type="submit" disabled={saving || !newReisaToken.trim()} style={{ marginTop: '0.5rem' }}>
              Update Token
            </button>
          </div>
        </form>

        <h3>API Key Management</h3>
        <div className="dev-admin-setting">
          <div className="dev-admin-setting__meta">
            <label>Generate New API Key</label>
            <p>Generate a brand new random API key. This will instantly invalidate the old key.</p>
            <div className="dev-admin-badges">
              <span className="dev-admin-badge dev-admin-badge--high">risk: high</span>
            </div>
          </div>
          <div className="dev-admin-setting__control">
            <button type="button" className="dev-admin-primary dev-admin-danger" disabled={saving} onClick={handleGenerateApiKey}>
              Generate New API Key
            </button>
          </div>
        </div>

        {error && <p className="dev-admin-form-error">{error}</p>}
        {message && <p className="dev-admin-save-message">{message}</p>}
      </article>
    </section>
  );
}
