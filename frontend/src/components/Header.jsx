import { BrainIcon, ActivityIcon, ShieldCheckIcon } from './Icons';

export const Header = ({ isRecording, memoryCount, isThinking }) => {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon-wrapper">
          <BrainIcon size={24} className="text-white" />
        </div>
        <div className="brand-text">
          <h1>ECHO</h1>
          <span className="brand-tagline">Your AI Memory</span>
        </div>
      </div>

      <div className="header-status">
        {isRecording ? (
          <div className="status-badge" style={{ background: 'rgba(244, 63, 94, 0.12)', borderColor: 'rgba(244, 63, 94, 0.3)', color: '#fda4af' }}>
            <span className="status-dot" style={{ backgroundColor: '#f43f5e', boxShadow: '0 0 8px #f43f5e' }}></span>
            <span>Recording Active</span>
          </div>
        ) : isThinking ? (
          <div className="status-badge" style={{ background: 'rgba(6, 182, 212, 0.12)', borderColor: 'rgba(6, 182, 212, 0.3)', color: '#67e8f9' }}>
            <span className="status-dot" style={{ backgroundColor: '#06b6d4', boxShadow: '0 0 8px #06b6d4' }}></span>
            <span>Recalling Memories...</span>
          </div>
        ) : (
          <div className="status-badge">
            <span className="status-dot"></span>
            <span>Memory Engine Ready</span>
          </div>
        )}

        <div className="stats-pill" title="Stored memories in local session">
          <ActivityIcon size={14} />
          <span>{memoryCount} Memories</span>
        </div>

        <div className="stats-pill" style={{ display: 'none' }}>
          <ShieldCheckIcon size={14} />
          <span>Explicit Consent</span>
        </div>
      </div>
    </header>
  );
};
