// frontend/src/dev-admin/help/HelpDrawerContext.js
//
// Lets a ContextualHelpLink open the Help drawer from anywhere in the admin
// tree (a Settings group header, a machine drawer, the restart banner)
// without prop-drilling through SettingsPanel, MachineCardsPanel or
// DevAdminShell. DevAdminPage is the only provider; outside it,
// useHelpDrawer() returns null and ContextualHelpLink renders nothing.

import { createContext, useContext } from 'react';

export const HelpDrawerContext = createContext(null);

export function useHelpDrawer() {
  return useContext(HelpDrawerContext);
}
