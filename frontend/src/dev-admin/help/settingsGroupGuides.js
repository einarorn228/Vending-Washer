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
  // Not settings-requiring-restart: none of this group's toggles is
  // restart-required, and that guide says so explicitly. admin-panel-orientation
  // discusses backend_relay_enabled and telemetry_enabled by name under
  // "What is high risk".
  runtime: 'admin-panel-orientation',
  codes: 'code-rejected',
  provider: 'reisa-configuration',
  // log_level is named in settings-requiring-restart's table, with where the
  // evidence of an applied restart appears; using-diagnostics never mentions it.
  logging: 'settings-requiring-restart',
};
