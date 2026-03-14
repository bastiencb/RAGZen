import { useState, useRef, useEffect } from "react";

const API_BASE = "http://localhost:8765";

// ─── Icônes SVG inline ───
const IconSend = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);
const IconFolder = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
  </svg>
);
const IconDatabase = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
  </svg>
);
const IconTrash = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
);
const IconBot = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/>
  </svg>
);
const IconUser = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
  </svg>
);
const IconInfo = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
  </svg>
);
const IconSearch = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);
const IconSettings = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);

// ─── Styles CSS ───
const styles = `
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:wght@400;500;600;700&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --bg-deep: #0a0c10;
    --bg-main: #0f1117;
    --bg-card: #161822;
    --bg-hover: #1c1f2e;
    --bg-input: #12141c;
    --border: #1e2235;
    --border-focus: #3b5bdb;
    --text-primary: #e2e4ed;
    --text-secondary: #8b8fa7;
    --text-muted: #5c6078;
    --accent: #5b7cfa;
    --accent-glow: rgba(91, 124, 250, 0.15);
    --accent-soft: #3b5bdb;
    --success: #40c057;
    --success-bg: rgba(64, 192, 87, 0.08);
    --warning: #fab005;
    --warning-bg: rgba(250, 176, 5, 0.08);
    --error: #ff6b6b;
    --error-bg: rgba(255, 107, 107, 0.08);
    --user-bubble: #1a2742;
    --bot-bubble: #161822;
    --radius: 12px;
    --radius-sm: 8px;
    --radius-lg: 16px;
    --shadow: 0 2px 12px rgba(0,0,0,0.3);
  }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--bg-deep);
    color: var(--text-primary);
    overflow: hidden;
    height: 100vh;
  }

  .app {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  /* ─── Sidebar ─── */
  .sidebar {
    width: 300px;
    min-width: 300px;
    background: var(--bg-main);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sidebar-header {
    padding: 20px;
    border-bottom: 1px solid var(--border);
  }

  .sidebar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
  }

  .sidebar-logo h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
    font-weight: 600;
    background: linear-gradient(135deg, var(--accent), #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }

  .sidebar-logo .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: 0 0 8px rgba(64, 192, 87, 0.5);
    animation: pulse-dot 2s infinite;
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .sidebar-subtitle {
    font-size: 12px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }

  .sidebar-section {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
  }

  .sidebar-section-title {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--text-muted);
    margin-bottom: 12px;
  }

  .folder-input-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .folder-input {
    display: flex;
    gap: 8px;
  }

  .folder-input input {
    flex: 1;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 12px;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    outline: none;
    transition: border-color 0.2s;
  }

  .folder-input input:focus {
    border-color: var(--border-focus);
  }

  .folder-input input::placeholder {
    color: var(--text-muted);
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--bg-card);
    color: var(--text-primary);
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .btn:hover {
    background: var(--bg-hover);
    border-color: var(--text-muted);
  }

  .btn:active {
    transform: scale(0.97);
  }

  .btn-primary {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
  }

  .btn-primary:hover {
    background: var(--accent-soft);
    border-color: var(--accent-soft);
  }

  .btn-danger {
    color: var(--error);
    border-color: transparent;
    background: transparent;
    padding: 6px 10px;
    font-size: 12px;
  }

  .btn-danger:hover {
    background: var(--error-bg);
  }

  .btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .index-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  /* ─── Status cards ─── */
  .status-cards {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .status-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
  }

  .status-card .status-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
  }

  .status-icon.online { background: var(--success-bg); color: var(--success); }
  .status-icon.offline { background: var(--error-bg); color: var(--error); }
  .status-icon.db { background: var(--accent-glow); color: var(--accent); }

  .status-info {
    flex: 1;
    min-width: 0;
  }

  .status-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .status-detail {
    font-size: 11px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Sources list ─── */
  .sources-section {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
  }

  .source-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 12px;
    color: var(--text-secondary);
    font-family: 'JetBrains Mono', monospace;
    word-break: break-all;
  }

  .source-item::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0.5;
    flex-shrink: 0;
  }

  .empty-sources {
    text-align: center;
    padding: 24px 12px;
    color: var(--text-muted);
    font-size: 13px;
    line-height: 1.6;
  }

  /* ─── Progress bar ─── */
  .progress-container {
    margin-top: 8px;
  }

  .progress-bar-bg {
    height: 4px;
    background: var(--bg-input);
    border-radius: 2px;
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), #8b5cf6);
    border-radius: 2px;
    transition: width 0.3s ease;
  }

  .progress-text {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 6px;
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Chat area ─── */
  .chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: var(--bg-deep);
    overflow: hidden;
  }

  .chat-header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-main);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .chat-header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .chat-header h2 {
    font-size: 15px;
    font-weight: 600;
  }

  .model-badge {
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    padding: 3px 8px;
    border-radius: 4px;
    background: var(--accent-glow);
    color: var(--accent);
    border: 1px solid rgba(91, 124, 250, 0.2);
  }

  .mode-toggle {
    display: flex;
    background: var(--bg-card);
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    overflow: hidden;
  }

  .mode-toggle button {
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'DM Sans', sans-serif;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .mode-toggle button.active {
    background: var(--accent);
    color: white;
  }

  .mode-toggle button:hover:not(.active) {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  /* ─── Messages ─── */
  .messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    scroll-behavior: smooth;
  }

  .messages-container::-webkit-scrollbar {
    width: 6px;
  }

  .messages-container::-webkit-scrollbar-track {
    background: transparent;
  }

  .messages-container::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 3px;
  }

  .message {
    display: flex;
    gap: 12px;
    max-width: 800px;
    width: 100%;
    margin: 0 auto;
    animation: msg-in 0.3s ease;
  }

  @keyframes msg-in {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .message.user {
    flex-direction: row-reverse;
  }

  .message-avatar {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .message.bot .message-avatar {
    background: linear-gradient(135deg, var(--accent), #8b5cf6);
    color: white;
  }

  .message.user .message-avatar {
    background: var(--user-bubble);
    color: var(--accent);
    border: 1px solid var(--border);
  }

  .message-content {
    padding: 12px 16px;
    border-radius: var(--radius);
    line-height: 1.65;
    font-size: 14px;
    max-width: 85%;
  }

  .message.bot .message-content {
    background: var(--bot-bubble);
    border: 1px solid var(--border);
    color: var(--text-primary);
  }

  .message.user .message-content {
    background: var(--user-bubble);
    border: 1px solid rgba(91, 124, 250, 0.15);
    color: var(--text-primary);
  }

  .message-content p { margin-bottom: 8px; }
  .message-content p:last-child { margin-bottom: 0; }

  .message-content code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    background: rgba(0,0,0,0.3);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .message-content pre {
    background: rgba(0,0,0,0.3);
    padding: 12px;
    border-radius: var(--radius-sm);
    overflow-x: auto;
    margin: 8px 0;
  }

  .message-content pre code {
    background: none;
    padding: 0;
  }

  .message-sources {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
  }

  .message-sources-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    margin-bottom: 6px;
    font-weight: 600;
  }

  .source-tag {
    display: inline-block;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    padding: 2px 8px;
    background: var(--accent-glow);
    color: var(--accent);
    border-radius: 4px;
    margin: 2px 4px 2px 0;
  }

  .similarity-tag {
    font-size: 10px;
    color: var(--text-muted);
    margin-left: 4px;
  }

  /* ─── Welcome screen ─── */
  .welcome {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    text-align: center;
  }

  .welcome-icon {
    width: 72px;
    height: 72px;
    border-radius: 20px;
    background: linear-gradient(135deg, var(--accent), #8b5cf6);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(91, 124, 250, 0.25);
  }

  .welcome-icon svg {
    width: 36px;
    height: 36px;
    color: white;
    stroke: white;
  }

  .welcome h2 {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .welcome p {
    color: var(--text-muted);
    font-size: 14px;
    max-width: 400px;
    line-height: 1.6;
  }

  .welcome-steps {
    margin-top: 28px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    text-align: left;
  }

  .welcome-step {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .welcome-step-num {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    background: var(--accent-glow);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
    font-family: 'JetBrains Mono', monospace;
  }

  /* ─── Input area ─── */
  .input-area {
    padding: 16px 24px 20px;
    background: var(--bg-main);
    border-top: 1px solid var(--border);
  }

  .input-wrapper {
    max-width: 800px;
    margin: 0 auto;
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }

  .input-box {
    flex: 1;
    position: relative;
  }

  .input-box textarea {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    color: var(--text-primary);
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    resize: none;
    outline: none;
    min-height: 46px;
    max-height: 160px;
    line-height: 1.5;
    transition: border-color 0.2s;
  }

  .input-box textarea:focus {
    border-color: var(--border-focus);
    box-shadow: 0 0 0 3px var(--accent-glow);
  }

  .input-box textarea::placeholder {
    color: var(--text-muted);
  }

  .send-btn {
    width: 46px;
    height: 46px;
    border-radius: var(--radius);
    border: none;
    background: var(--accent);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
    flex-shrink: 0;
  }

  .send-btn:hover:not(:disabled) {
    background: var(--accent-soft);
    transform: scale(1.05);
  }

  .send-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  /* ─── Typing indicator ─── */
  .typing {
    display: flex;
    gap: 4px;
    padding: 4px 0;
  }

  .typing span {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--text-muted);
    animation: bounce 1.4s infinite;
  }

  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }

  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
  }

  /* ─── Settings panel ─── */
  .settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
  }

  .settings-label {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .settings-value {
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-primary);
  }

  .settings-input {
    width: 60px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 4px 8px;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    text-align: center;
    outline: none;
  }

  .settings-input:focus {
    border-color: var(--border-focus);
  }

  /* ─── Notification ─── */
  .notification {
    position: fixed;
    top: 16px;
    right: 16px;
    padding: 12px 20px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    font-weight: 500;
    z-index: 100;
    animation: notif-in 0.3s ease;
    box-shadow: var(--shadow);
  }

  .notification.success {
    background: #1a2e1a;
    border: 1px solid rgba(64, 192, 87, 0.3);
    color: var(--success);
  }

  .notification.error {
    background: #2e1a1a;
    border: 1px solid rgba(255, 107, 107, 0.3);
    color: var(--error);
  }

  .notification.info {
    background: #1a1a2e;
    border: 1px solid rgba(91, 124, 250, 0.3);
    color: var(--accent);
  }

  @keyframes notif-in {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
  }
`;

// ─── Composant principal ───
export default function RAGChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexProgress, setIndexProgress] = useState({ current: 0, total: 0, file: "" });
  const [isGenerating, setIsGenerating] = useState(false);
  const [mode, setMode] = useState("ask"); // "ask" or "search"
  const [status, setStatus] = useState({ ollama: false, models: [], dbCount: 0, sources: [] });
  const [topK, setTopK] = useState(5);
  const [notification, setNotification] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const notify = (message, type = "info") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // ─── Mock API (remplacer par les vrais appels au backend) ───
  // En production, ces fonctions appellent le serveur Python (FastAPI/Flask)
  // qui orchestre ChromaDB + Ollama. Ici on simule pour la démo.

  const apiCall = async (endpoint, data = {}) => {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`Erreur serveur : ${res.status}`);
    return res.json();
  };

  const checkStatus = async () => {
    try {
      const data = await apiCall("/status");
      setStatus(data);
    } catch {
      // Backend non connecté — mode démo
      setStatus({ ollama: false, models: [], dbCount: 0, sources: [] });
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleIndex = async () => {
    if (!folderPath.trim()) {
      notify("Indique le chemin du dossier à indexer", "error");
      return;
    }
    setIsIndexing(true);
    setIndexProgress({ current: 0, total: 0, file: "Analyse du dossier..." });

    try {
      const data = await apiCall("/index", { folder: folderPath.trim() });
      setIndexProgress({ current: data.total, total: data.total, file: "Terminé !" });
      notify(`${data.new_chunks} chunks ajoutés depuis ${data.files_processed} fichier(s)`, "success");
      checkStatus();
    } catch (e) {
      notify(`Erreur d'indexation : ${e.message}`, "error");
    } finally {
      setTimeout(() => setIsIndexing(false), 1500);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Supprimer toute la base vectorielle ?")) return;
    try {
      await apiCall("/reset");
      notify("Base vectorielle réinitialisée", "success");
      checkStatus();
    } catch (e) {
      notify(`Erreur : ${e.message}`, "error");
    }
  };

  const handleSend = async () => {
    const question = input.trim();
    if (!question || isGenerating) return;

    const userMsg = { role: "user", content: question, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsGenerating(true);

    if (textareaRef.current) {
      textareaRef.current.style.height = "46px";
    }

    try {
      const endpoint = mode === "ask" ? "/ask" : "/search";
      const data = await apiCall(endpoint, { query: question, top_k: topK });

      const botMsg = {
        role: "bot",
        content: data.answer || data.results?.map((r, i) =>
          `**[${i + 1}] ${r.source}** (${(r.similarity * 100).toFixed(0)}%)\n${r.text}`
        ).join("\n\n"),
        sources: data.sources || data.results?.map((r) => ({
          name: r.source,
          similarity: r.similarity,
        })),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          content: `Erreur de communication avec le backend.\nVérifie que le serveur Python tourne sur ${API_BASE}.\n\nDétail : ${e.message}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const autoResize = (e) => {
    e.target.style.height = "46px";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  const formatContent = (text) => {
    if (!text) return null;
    return text.split("\n").map((line, i) => {
      // Bold
      const parts = line.split(/\*\*(.*?)\*\*/g);
      return (
        <p key={i}>
          {parts.map((part, j) =>
            j % 2 === 1 ? <strong key={j}>{part}</strong> : part
          )}
        </p>
      );
    });
  };

  return (
    <>
      <style>{styles}</style>
      <div className="app">
        {/* ─── Sidebar ─── */}
        <div className="sidebar">
          <div className="sidebar-header">
            <div className="sidebar-logo">
              <h1>RAG Local</h1>
              <div className={`dot ${status.ollama ? "" : ""}`}
                style={{ background: status.ollama ? "#40c057" : "#ff6b6b" }} />
            </div>
            <div className="sidebar-subtitle">chromadb + ollama</div>
          </div>

          {/* Indexation */}
          <div className="sidebar-section">
            <div className="sidebar-section-title">Indexation</div>
            <div className="folder-input-group">
              <div className="folder-input">
                <input
                  type="text"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  placeholder="/chemin/vers/documents"
                  disabled={isIndexing}
                  onKeyDown={(e) => e.key === "Enter" && handleIndex()}
                />
              </div>
              <div className="index-actions">
                <button className="btn btn-primary" onClick={handleIndex}
                  disabled={isIndexing || !folderPath.trim()}
                  style={{ flex: 1 }}>
                  <IconFolder /> {isIndexing ? "Indexation..." : "Indexer"}
                </button>
                <button className="btn btn-danger" onClick={handleReset}
                  disabled={isIndexing} title="Réinitialiser la base">
                  <IconTrash />
                </button>
              </div>
              {isIndexing && (
                <div className="progress-container">
                  <div className="progress-bar-bg">
                    <div className="progress-bar-fill"
                      style={{ width: indexProgress.total ? `${(indexProgress.current / indexProgress.total) * 100}%` : "30%",
                        transition: indexProgress.total ? "width 0.3s" : "width 2s",
                        ...(indexProgress.total ? {} : { animation: "none", width: "60%" })
                      }} />
                  </div>
                  <div className="progress-text">{indexProgress.file}</div>
                </div>
              )}
            </div>
          </div>

          {/* Statut */}
          <div className="sidebar-section">
            <div className="sidebar-section-title">Statut</div>
            <div className="status-cards">
              <div className="status-card">
                <div className={`status-icon ${status.ollama ? "online" : "offline"}`}>
                  {status.ollama ? "✓" : "✗"}
                </div>
                <div className="status-info">
                  <div className="status-label">Ollama</div>
                  <div className="status-detail">
                    {status.ollama ? `${status.models.length} modèle(s)` : "non connecté"}
                  </div>
                </div>
              </div>
              <div className="status-card">
                <div className="status-icon db"><IconDatabase /></div>
                <div className="status-info">
                  <div className="status-label">ChromaDB</div>
                  <div className="status-detail">{status.dbCount} chunks</div>
                </div>
              </div>
            </div>
          </div>

          {/* Settings */}
          <div className="sidebar-section">
            <div className="sidebar-section-title" style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}
              onClick={() => setShowSettings(!showSettings)}>
              <IconSettings /> Paramètres
            </div>
            {showSettings && (
              <div>
                <div className="settings-row">
                  <span className="settings-label">Résultats (top_k)</span>
                  <input className="settings-input" type="number" min="1" max="20"
                    value={topK} onChange={(e) => setTopK(parseInt(e.target.value) || 5)} />
                </div>
                <div className="settings-row">
                  <span className="settings-label">Embedding</span>
                  <span className="settings-value">bge-m3</span>
                </div>
                <div className="settings-row">
                  <span className="settings-label">LLM</span>
                  <span className="settings-value">mistral-nemo</span>
                </div>
              </div>
            )}
          </div>

          {/* Documents indexés */}
          <div className="sources-section">
            <div className="sidebar-section-title">Documents indexés</div>
            {status.sources?.length > 0 ? (
              status.sources.map((s, i) => (
                <div className="source-item" key={i}>{s}</div>
              ))
            ) : (
              <div className="empty-sources">
                Aucun document indexé.<br />
                Indique un dossier ci-dessus pour commencer.
              </div>
            )}
          </div>
        </div>

        {/* ─── Chat ─── */}
        <div className="chat-area">
          <div className="chat-header">
            <div className="chat-header-left">
              <h2>Chat</h2>
              <span className="model-badge">mistral-nemo:12b</span>
            </div>
            <div className="mode-toggle">
              <button className={mode === "ask" ? "active" : ""}
                onClick={() => setMode("ask")}>
                <IconBot /> RAG
              </button>
              <button className={mode === "search" ? "active" : ""}
                onClick={() => setMode("search")}>
                <IconSearch /> Recherche
              </button>
            </div>
          </div>

          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon"><IconBot /></div>
              <h2>RAG Local</h2>
              <p>Interroge tes documents en langage naturel, tout tourne en local sur ta machine.</p>
              <div className="welcome-steps">
                <div className="welcome-step">
                  <span className="welcome-step-num">1</span>
                  <span>Indique le chemin d'un dossier dans la barre latérale et lance l'indexation</span>
                </div>
                <div className="welcome-step">
                  <span className="welcome-step-num">2</span>
                  <span>Pose une question — le système retrouve les passages pertinents et génère une réponse</span>
                </div>
                <div className="welcome-step">
                  <span className="welcome-step-num">3</span>
                  <span>Bascule en mode <strong>Recherche</strong> pour voir les extraits bruts sans reformulation</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="messages-container">
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === "bot" ? <IconBot /> : <IconUser />}
                  </div>
                  <div className="message-content">
                    {formatContent(msg.content)}
                    {msg.sources?.length > 0 && (
                      <div className="message-sources">
                        <div className="message-sources-title">Sources</div>
                        {msg.sources.map((s, j) => (
                          <span key={j} className="source-tag">
                            {s.name}
                            {s.similarity && (
                              <span className="similarity-tag">
                                {(s.similarity * 100).toFixed(0)}%
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isGenerating && (
                <div className="message bot">
                  <div className="message-avatar"><IconBot /></div>
                  <div className="message-content">
                    <div className="typing">
                      <span /><span /><span />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Input */}
          <div className="input-area">
            <div className="input-wrapper">
              <div className="input-box">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => { setInput(e.target.value); autoResize(e); }}
                  onKeyDown={handleKeyDown}
                  placeholder={mode === "ask"
                    ? "Pose une question sur tes documents..."
                    : "Recherche sémantique dans tes documents..."}
                  rows={1}
                  disabled={isGenerating}
                />
              </div>
              <button className="send-btn" onClick={handleSend}
                disabled={!input.trim() || isGenerating}>
                <IconSend />
              </button>
            </div>
          </div>
        </div>

        {/* Notification */}
        {notification && (
          <div className={`notification ${notification.type}`}>
            {notification.message}
          </div>
        )}
      </div>
    </>
  );
}
