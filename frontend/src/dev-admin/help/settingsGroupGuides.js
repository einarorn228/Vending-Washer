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
  // No entry for machine_timing: this group is button_select_timeout_sec and
  // machine_reservation_minutes. machine-does-not-start covers the latter by
  // name, but its own "When to use this" section presupposes the machine was
  // already chosen ("the customer chose a machine on the kiosk ... and the
  // machine still never runs") — the opposite of an armed-code-timeout
  // problem, which is what button_select_timeout_sec governs. No guide in the
  // corpus mentions button_select_timeout_sec at all, so there is nothing to
  // retarget to. Half the group would open a guide that frames itself as not
  // applying to their situation, which is worse than no icon.
  screen_timing: 'admin-panel-orientation',
  // hardware_timing is relay_pulse_duration_sec, shelly_http_timeout_sec,
  // telemetry_http_timeout_sec. machine-technical-mapping names two of the
  // three explicitly ("`shelly_http_timeout_sec` and
  // `telemetry_http_timeout_sec` decide how long the backend waits for that
  // device before treating the command or the read as failed"), which is
  // better coverage than machine-does-not-start's one of three. No guide in
  // the corpus mentions relay_pulse_duration_sec.
  hardware_timing: 'machine-technical-mapping',
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
