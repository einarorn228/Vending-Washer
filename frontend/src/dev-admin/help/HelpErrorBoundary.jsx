// frontend/src/dev-admin/help/HelpErrorBoundary.jsx
//
// Wraps HelpPanel and HelpDrawer so a render fault anywhere in the Help Hub
// (a malformed guide payload, an unexpected block type, a search throw)
// never unmounts the rest of the admin shell (spec §11.4). Falls back to
// the same `unavailable` string used when the manifest fetch itself fails.

import React from 'react';
import { t } from './helpStrings.js';

export default class HelpErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch() {
    // Nothing to report to — the fallback string below is the entire contract.
  }

  componentDidUpdate(prevProps) {
    // A different guide/tab/locale after a caught error should get a fresh
    // attempt rather than being stuck on the fallback forever.
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (this.state.hasError) {
      return <p className="dev-admin-warning dev-admin-helphub-unavailable">{t(this.props.locale, 'unavailable')}</p>;
    }
    return this.props.children;
  }
}
