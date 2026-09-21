'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Card, Spinner } from '@/components/ui';

const API = 'http://localhost:8000';

const TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'SPY', 'QQQ', 'BTC-USD', 'ETH-USD'];

const SUGGESTIONS = [
  'Should I buy AAPL right now?',
  'Optimize a portfolio with MSFT, NVDA, and SPY',
  'What is the best strategy for TSLA?',
  'Why does the model predict NVDA will go up?',
  'What is the latest news on GOOGL?',
  'Analyze AAPL and give me a recommendation',
  'Compare MSFT vs NVDA for long-term holding',
  'What is the risk of a portfolio with 40% NVDA?',
];

interface Message {
  role: 'user' | 'assistant';
  content: string;
  tools_used?: string[];
  loading?: boolean;
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `👋 Hello! I'm QuantAI's AI Financial Assistant.\n\nI can help you with:\n• **Predictions** — Should I buy/sell a specific stock?\n• **Portfolio optimization** — Best allocation across multiple assets\n• **Strategy analysis** — Which trading strategy works best?\n• **Explainability** — Why is the model predicting up/down?\n• **News** — Latest sentiment on any ticker\n\nAsk me anything about your portfolio!`,
    },
  ]);
  const [input, setInput]     = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = useCallback(async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    setInput('');
    const history = messages
      .filter(m => !m.loading)
      .map(m => ({ role: m.role, content: m.content }));

    setMessages(prev => [
      ...prev,
      { role: 'user', content: msg },
      { role: 'assistant', content: '', loading: true },
    ]);
    setLoading(true);

    try {
      const r = await fetch(`${API}/api/v1/assistant/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, history }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || r.statusText);

      setMessages(prev => {
        const next = [...prev];
        next[next.length - 1] = {
          role: 'assistant',
          content: data.response || data.message || 'No response',
          tools_used: (data.tools_used || []).map((t: any) =>
            typeof t === 'string' ? t : t?.tool || t?.name || JSON.stringify(t)
          ),
        };
        return next;
      });
    } catch (e: any) {
      setMessages(prev => {
        const next = [...prev];
        next[next.length - 1] = {
          role: 'assistant',
          content: `❌ Error: ${e.message}. Make sure the AI Assistant backend is deployed.`,
        };
        return next;
      });
    } finally {
      setLoading(false);
    }
  }, [input, messages, loading]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const clearChat = () => {
    setMessages([{ role: 'assistant', content: 'Chat cleared. How can I help you?' }]);
  };

  const formatContent = (text: string) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-surface px-1 rounded text-accent font-mono text-xs">$1</code>')
      .replace(/\n/g, '<br/>');
  };

  return (
    <div className="flex flex-col p-6 gap-4" style={{ height: 'calc(100vh - 0px)' }}>
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">AI Financial Assistant</h1>
          <p className="text-sm text-muted mt-1">Powered by Claude API · 5 financial tools · RAG</p>
        </div>
        <button
          onClick={clearChat}
          className="text-xs text-muted hover:text-[#e8edf5] border border-border rounded px-3 py-1.5 transition-colors"
        >
          Clear chat
        </button>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Suggestions sidebar */}
        <div className="w-52 flex-shrink-0 space-y-3 overflow-y-auto">
          <Card>
            <p className="text-xs text-muted font-medium uppercase tracking-wider mb-3">Quick questions</p>
            <div className="space-y-1">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => send(s)}
                  disabled={loading}
                  className="w-full text-left text-xs text-muted hover:text-[#e8edf5] hover:bg-white/[0.03] rounded p-2 transition-colors disabled:opacity-40"
                >
                  {s}
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <p className="text-xs text-muted font-medium uppercase tracking-wider mb-3">Quick analyze</p>
            <div className="space-y-1">
              {TICKERS.slice(0, 6).map(t => (
                <button
                  key={t}
                  onClick={() => send(`Analyze ${t} and give me a detailed recommendation`)}
                  disabled={loading}
                  className="w-full text-left font-mono text-xs text-accent hover:bg-accent/10 rounded px-2 py-1.5 transition-colors disabled:opacity-40"
                >
                  {t} →
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col min-h-0 gap-3">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className="max-w-[85%]">
                  <div className={`flex items-start gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      m.role === 'user' ? 'bg-accent text-bg' : 'bg-surface border border-border text-accent'
                    }`}>
                      {m.role === 'user' ? 'U' : '◆'}
                    </div>
                    <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-accent text-bg font-medium'
                        : 'bg-surface border border-border text-[#e8edf5]'
                    }`}>
                      {m.loading ? (
                        <div className="flex items-center gap-2 text-muted">
                          <Spinner />
                          <span className="text-xs">Analyzing with AI + financial tools…</span>
                        </div>
                      ) : (
                        <div dangerouslySetInnerHTML={{ __html: formatContent(m.content) }} />
                      )}
                      {m.tools_used && m.tools_used.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-border/50 flex flex-wrap gap-1">
                          {m.tools_used.map((t, j) => (
                            <span key={j} className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full">
                              🔧 {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex-shrink-0">
            <div className="flex gap-2 items-end bg-surface border border-border rounded-xl p-3">
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about your portfolio, predictions, strategies, news… (Enter to send)"
                rows={2}
                className="flex-1 bg-transparent text-[#e8edf5] text-sm resize-none outline-none placeholder:text-muted leading-relaxed"
              />
              <button
                onClick={() => send()}
                disabled={loading || !input.trim()}
                className="bg-accent text-bg font-bold px-4 py-2 rounded-lg hover:bg-accent/80 disabled:opacity-40 transition-colors text-sm flex-shrink-0"
              >
                {loading ? '⏳' : '→ Send'}
              </button>
            </div>
            <p className="text-xs text-muted mt-1 text-center">
              Claude API · RAG + 5 tools: prediction, portfolio, backtest, news, SHAP
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
