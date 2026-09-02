// Plain-language explanations shown in a hover tooltip on the dev-admin Settings
// page, so any admin can understand what a setting does before changing it.
// Keyed by the setting `key` from the backend SETTING_SCHEMA. Keep the language
// simple and non-technical on purpose.
export const SETTING_HELP = {
  dev_admin_enabled:
    'Master on/off switch for this admin panel itself. If you turn this OFF, this whole page stops working and can only be turned back on from the server. Leave it ON while you need admin access.',
  api_key:
    'The secret key that apps use to talk to the backend. It also works as the admin password. Shown masked for safety — the real value is never displayed or edited here.',
  admin_username:
    'The username for the browser login pop-up on admin pages. Read-only here.',
  admin_password_hash:
    'The scrambled (hashed) version of the admin password. The real password is never stored or shown. Read-only here.',
  cors_allowed_origins:
    'The list of website addresses allowed to call the backend from a browser. Only add addresses you trust. Getting this wrong can stop the kiosk or admin page from loading. Usually needs a restart.',
  serial_port:
    'Which USB port the QR-code scanner is plugged into (for example /dev/ttyACM0). If the scanner stops reading codes, it may be pointing at the wrong port. Needs a restart to take effect.',
  serial_baudrate:
    "The speed the backend uses to talk to the QR scanner. It must match the scanner's own setting (9600 is typical). A wrong value means garbled scans or none at all. Needs a restart.",
  scan_timeout:
    'How many seconds the backend waits while reading from the scanner before giving up on a single read. Rarely needs changing. Needs a restart.',
  button_select_timeout_sec:
    'After a code is scanned, how many seconds the customer has to pick a machine before the code is cancelled and the screen resets. (Applies to the physical button box.)',
  machine_reservation_minutes:
    "After a customer picks a machine, how many minutes it's held for them before it becomes available to someone else again.",
  backend_relay_enabled:
    'The big one: when ON, choosing a machine actually switches on real power to it. When OFF, the app only pretends to start machines (safe test mode). Only turn ON once the wiring is confirmed correct.',
  telemetry_enabled:
    "When ON, the backend keeps checking the sensors to see which machines are really running, so availability is correct. When OFF, every machine looks 'available' even if it's in use.",
  button_box_enabled:
    'Lets customers pick a machine using the physical push-button box as well as the touchscreen. Leave OFF if you only want touchscreen selection.',
  provider_default:
    "Where codes are checked. 'local' = codes kept in this machine's own database. 'reisa' = codes checked with the external Reisa system. This changes how every scan is validated.",
  provider_reisa_enabled:
    "A safety gate that must be ON for the 'reisa' option above to actually work. If this is OFF, the app falls back to local codes even when 'reisa' is selected.",
  reisa_base_url:
    "The web address of the Reisa server the app talks to. Point this at the correct live or test Reisa system — a wrong address means codes can't be validated.",
  reisa_bearer_token:
    'The secret token used to log in to Reisa. Shown masked for safety — set or changed elsewhere, never displayed here.',
  log_level:
    'How much detail the backend writes to its log files. INFO is normal. DEBUG records everything (handy for troubleshooting, but noisy). ERROR records only problems. Needs a restart.',
  kiosk_input_mode:
    "Left over from an earlier design. It is reported to the kiosk but currently changes nothing \u2014 customers can always tap a machine on the touchscreen. To turn the physical button box on or off, use 'Button box input enabled' instead.",
  code_expiration_days:
    'How many days a newly created code stays valid. 0 means codes never expire. Changing this does not affect codes that already exist \u2014 only ones made afterwards.',
  selection_notice_seconds:
    "How long the 'starting your machine' screen stays up while waiting for the machine to actually report that it is running. If it gives up too soon, raise this.",
  started_notice_seconds:
    'After the machine is confirmed running, how long the confirmation screen stays up before the kiosk goes back to the scan screen. Raise it if customers walk away before reading it.',
  error_notice_seconds:
    'How long an error message stays on screen before the kiosk resets itself and is ready for the next customer.',
  kiosk_poll_interval_ms:
    'How often (in milliseconds) the kiosk screen checks in with the backend. 1000 = once per second. Lower feels more responsive but works the Pi harder; higher is gentler but the screen updates more slowly.',
  relay_pulse_duration_sec:
    'How long the relay stays closed when the system sends a short "press" to a machine. Some machines ignore a pulse that is too short \u2014 if a machine does not react, try a longer value.',
  shelly_http_timeout_sec:
    'How long the backend waits for a Shelly relay to answer a command before treating it as failed. Raise this if the Wi-Fi to the machines is slow or unreliable.',
  telemetry_http_timeout_sec:
    'How long the backend waits when reading power/voltage from a machine sensor before counting it as a failed reading. Raise this on a busy or weak Wi-Fi network.',
  reisa_connect_timeout_ms:
    'How long to wait (in milliseconds) while first connecting to the Reisa server. Too low and normal slow moments look like outages.',
  reisa_read_timeout_ms:
    'How long to wait (in milliseconds) for Reisa to answer once connected. Set this above the slowest response you see in practice.',
  reisa_action_start:
    'The exact wording sent to Reisa when a machine starts. This must match what Reisa expects \u2014 a wrong value makes Reisa reject every start. Do not change without checking with Reisa.',
  reisa_action_completion:
    'The exact wording sent to Reisa when a wash finishes. Must match what Reisa expects. Do not change without checking with Reisa.',
  reisa_retry_worker_enabled:
    'When ON, a background helper automatically retries messages to Reisa that failed for a temporary reason (like a brief network drop). Recommended ON when using Reisa.',
  reisa_retry_worker_interval_sec:
    'How often the retry helper looks for failed Reisa messages waiting to be sent again.',
  reisa_retry_worker_batch_size:
    'How many failed Reisa messages the retry helper handles in one go. Higher clears a backlog faster but does more work at once.',
};
