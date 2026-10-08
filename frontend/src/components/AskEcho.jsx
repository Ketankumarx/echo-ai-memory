import { useState } from 'react';
import { SparklesIcon, SendIcon, ExternalLinkIcon, BrainIcon } from './Icons';

export const AskEcho = ({ memories }) => {
  const [inputQuery, setInputQuery] = useState('');
  const [chatMessages, setChatMessages] = useState([
    {
      id: 'msg-welcome',
      sender: 'echo',
      text: "Hello! I'm ECHO, your personal memory assistant. Ask me anything about your past conversations, decisions, or suggestions.",
      citations: [],
      webSources: [],
      timestamp: 'Just now'
    }
  ]);
  const [isThinking, setIsThinking] = useState(false);

  // Dynamic suggested queries based on actual memories or demo flow
  const suggestedQueries = [
    "What did Rahul tell me about the hackathon?",
    "What technologies did he suggest?",
    "What did Priya say about judging criteria?",
    "What did Rahul tell me about quantum computing?"
  ];

  const handleSend = async (textToSend) => {
    const query = (textToSend || inputQuery).trim();
    if (!query || isThinking) return;

    // 1. Add user message to chat
    const userMsg = {
      id: `msg-user-${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: 'Just now'
    };

    setChatMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setIsThinking(true);

    try {
      // 2. Real API call to FastAPI backend
      const response = await fetch('/api/memories/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          enable_web_grounding: true
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned ${response.status}`);
      }

      const data = await response.json();

      // 3. Build citation badges from real referenced memories
      const citations = (data.memories_referenced || []).map(m => ({
        id: m.id,
        label: `${m.person || m.subject || 'Memory'} • ${m.topic || m.category || 'Note'}`,
        fact: m.fact || m.full_fact
      }));

      const echoMsg = {
        id: `msg-echo-${Date.now()}`,
        sender: 'echo',
        text: data.answer,
        citations: citations,
        webGrounded: Boolean(data.web_grounded),
        webSources: data.web_sources || [],
        webSearchQuery: data.web_search_query,
        timestamp: 'Just now'
      };

      setChatMessages(prev => [...prev, echoMsg]);
    } catch (err) {
      console.error("Ask ECHO query failed:", err);
      const errorEchoMsg = {
        id: `msg-echo-error-${Date.now()}`,
        sender: 'echo',
        text: `I encountered an error querying memories: ${err.message}. Please check if the backend is running.`,
        citations: [],
        timestamp: 'Just now'
      };
      setChatMessages(prev => [...prev, errorEchoMsg]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="glass-panel chat-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <SparklesIcon size={20} />
          <span>Ask ECHO</span>
        </h2>
        <span className="stats-pill" style={{ color: 'var(--accent-cyan-light)', borderColor: 'rgba(6, 182, 212, 0.3)' }}>
          Semantic Recall
        </span>
      </div>

      {/* Suggested Prompt Chips */}
      <div className="suggested-prompts">
        {suggestedQueries.map((q, idx) => (
          <button
            key={idx}
            className="suggestion-chip"
            onClick={() => handleSend(q)}
            disabled={isThinking}
            title={`Ask: "${q}"`}
          >
            <BrainIcon size={12} />
            <span>{q}</span>
          </button>
        ))}
      </div>

      {/* Chat Messages Stream */}
      <div className="chat-history">
        {chatMessages.map(msg => (
          <div key={msg.id} className={`chat-bubble ${msg.sender}`}>
            {msg.sender === 'echo' && (
              <div className="echo-sender">
                <BrainIcon size={14} />
                <span>ECHO</span>
              </div>
            )}

            <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
              {msg.text}
            </div>

            {/* Citations & Sources */}
            {((msg.citations && msg.citations.length > 0) || msg.webGrounded) && (
              <div className="echo-citations">
                <span className="citation-title">Sources Cited</span>
                <div className="citation-badges">
                  {msg.citations && msg.citations.map(cit => (
                    <span
                      key={cit.id}
                      className="citation-pill"
                      title={cit.fact || "Retrieved from your personal memory database"}
                    >
                      <BrainIcon size={10} />
                      <span>{cit.label}</span>
                    </span>
                  ))}
                  {msg.webGrounded && (
                    <span className="serp-preview-badge" title="Grounded with live Google search via SerpApi">
                      <ExternalLinkIcon size={10} />
                      <span>SerpApi Grounded</span>
                    </span>
                  )}
                </div>

                {/* Web source links if returned from SerpApi */}
                {msg.webSources && msg.webSources.length > 0 && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {msg.webSources.map((ws, i) => (
                      <a
                        key={i}
                        href={ws.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: '0.74rem',
                          color: 'var(--accent-cyan-light)',
                          textDecoration: 'none',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        <ExternalLinkIcon size={11} />
                        <span>{ws.title || ws.link}</span>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {isThinking && (
          <div className="chat-bubble echo">
            <div className="loading-pulse">
              <BrainIcon size={14} style={{ color: 'var(--accent-cyan)' }} />
              <span>ECHO is recalling past memories...</span>
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Chat Input Bar */}
      <div className="chat-input-bar">
        <input
          id="input-chat-query"
          type="text"
          className="chat-input"
          placeholder="Ask ECHO about past conversations, decisions, or suggestions..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isThinking}
        />
        <button
          id="btn-send-query"
          className="btn-primary"
          onClick={() => handleSend()}
          title="Ask ECHO"
          disabled={!inputQuery.trim() || isThinking}
        >
          <SendIcon size={16} />
          <span>Ask</span>
        </button>
      </div>
    </div>
  );
};
