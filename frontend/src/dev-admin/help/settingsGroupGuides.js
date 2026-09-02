// frontend/src/dev-admin/help/settingsGroupGuides.js
//
// The 15-guide corpus has no per-settings-group guides, so each Settings group
// header's contextual link resolves through this static map keyed by the
// backend's SETTING_GROUPS id (backend/services/dev_admin_service.py). A group
// with no entry here renders no link. Surfaced at the Task 15 checkpoint for
// maintainer retargeting as the guide corpus grows.
export const SETTINGS_GROUP_GUIDES = {
  dev_admin: 'admin-access-recovery',
  api_security: 'admin-access-recovery',
  scanner: 'scanner-not-scanning',
  machine_timing: 'machine-does-not-start',
  screen_timing: 'admin-panel-orientation',
  hardware_timing: 'machine-does-not-start',
  kiosk: 'admin-panel-orientation',
  runtime: 'settings-requiring-restart',
  codes: 'code-rejected',
  provider: 'reisa-configuration',
  logging: 'using-diagnostics',
};
