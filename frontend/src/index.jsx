import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.jsx';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      const msg = this.state.error?.message || String(this.state.error);
      return (
        <div
          style={{
            boxSizing: 'border-box',
            minHeight: '100vh',
            padding: '1.5rem',
            color: '#1a1a1a',
            background: '#fff3f3',
            fontFamily: 'system-ui, sans-serif',
          }}
        >
          <h1 style={{ fontSize: 'clamp(1.1rem, 4vw, 1.4rem)' }}>UI error</h1>
          <p style={{ fontFamily: 'monospace', wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}>
            {msg}
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}

const el = document.getElementById('root');
if (!el) {
  throw new Error('Missing #root element');
}

const root = createRoot(el);
root.render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
