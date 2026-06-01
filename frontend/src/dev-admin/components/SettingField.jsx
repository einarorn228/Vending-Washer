import React from 'react';

export default function SettingField({ setting, value, error, onChange }) {
  const inputId = `setting-${setting.key}`;
  const editable = Boolean(setting.editable);

  function renderControl() {
    if (setting.type === 'secret') {
      return <span className="dev-admin-secret">{setting.is_set ? 'Set / masked' : 'Not set'}</span>;
    }
    if (setting.type === 'bool') {
      return (
        <select id={inputId} value={String(Boolean(value))} disabled={!editable} onChange={(event) => onChange(setting.key, event.target.value === 'true')}>
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      );
    }
    if (setting.type === 'enum') {
      return (
        <select id={inputId} value={value ?? ''} disabled={!editable} onChange={(event) => onChange(setting.key, event.target.value)}>
          {(setting.choices || []).map((choice) => <option key={choice} value={choice}>{choice}</option>)}
        </select>
      );
    }
    if (setting.type === 'int' || setting.type === 'float') {
      return <input id={inputId} type="number" value={value ?? ''} disabled={!editable} onChange={(event) => onChange(setting.key, event.target.value)} />;
    }
    if (setting.type === 'list') {
      const text = Array.isArray(value) ? value.join(',') : value ?? '';
      return <textarea id={inputId} value={text} disabled={!editable} onChange={(event) => onChange(setting.key, event.target.value)} rows={2} />;
    }
    return <input id={inputId} type="text" value={value ?? ''} disabled={!editable} onChange={(event) => onChange(setting.key, event.target.value)} />;
  }

  return (
    <div className={`dev-admin-setting ${!editable ? 'is-readonly' : ''}`}>
      <div className="dev-admin-setting__meta">
        <label htmlFor={inputId}>{setting.label}</label>
        <p>{setting.description}</p>
        <div className="dev-admin-badges">
          <span className={`dev-admin-badge dev-admin-badge--${setting.risk || 'low'}`}>risk: {setting.risk || 'low'}</span>
          {setting.restart_required ? <span className="dev-admin-badge dev-admin-badge--restart">restart required</span> : <span className="dev-admin-badge">applies without restart</span>}
          {!editable ? <span className="dev-admin-badge">read-only</span> : null}
        </div>
      </div>
      <div className="dev-admin-setting__control">
        {renderControl()}
        {error ? <p className="dev-admin-form-error">{error}</p> : null}
      </div>
    </div>
  );
}
