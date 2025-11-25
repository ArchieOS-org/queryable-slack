'use client';

import { useState, useRef, FormEvent } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from '@/components/ui/card';

interface Source {
  date: string;
  channel: string;
  message_count: number;
}

interface ApiResponse {
  answer: string;
  sources: Source[];
  query: string;
  retrieval_count?: number;
  error?: string;
}

type QueryStatus = 'idle' | 'loading' | 'success' | 'error';

interface QueryState {
  status: QueryStatus;
  query: string;
  answer: string | null;
  sources: Source[];
  retrievalCount: number;
  error: string | null;
}

const initialState: QueryState = {
  status: 'idle',
  query: '',
  answer: null,
  sources: [],
  retrievalCount: 0,
  error: null,
};

const SUGGESTIONS = [
  'Who handles listing drafts?',
  'Recent client communications',
  'Property negotiation history',
];

export function EveryAvenueChat() {
  const [state, setState] = useState<QueryState>(initialState);
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const query = inputValue.trim();
    if (!query || state.status === 'loading') return;

    setState({
      ...initialState,
      status: 'loading',
      query,
    });
    setInputValue('');

    try {
      const response = await fetch('/api/index', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, match_count: 40 }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Request failed: ${response.status}`);
      }

      const data: ApiResponse = await response.json();

      setState({
        status: 'success',
        query,
        answer: data.answer || 'No response received.',
        sources: data.sources || [],
        retrievalCount: data.retrieval_count || 0,
        error: null,
      });
    } catch (err) {
      setState({
        status: 'error',
        query,
        answer: null,
        sources: [],
        retrievalCount: 0,
        error: err instanceof Error ? err.message : 'An unexpected error occurred',
      });
    }
  };

  const handleReset = () => {
    setState(initialState);
    setInputValue('');
    setSourcesExpanded(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    inputRef.current?.focus();
  };

  const isIdle = state.status === 'idle';
  const isLoading = state.status === 'loading';
  const hasResult = state.status === 'success' || state.status === 'error';

  return (
    <div className="min-h-screen bg-[var(--background)] flex flex-col">
      {/* Header - Always visible */}
      <header className="flex-shrink-0 border-b border-[var(--border)] bg-[var(--background)]/80 backdrop-blur-sm sticky top-0 z-10 safe-top">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src="https://widgets.oakvillechamber.com/feeds/membershipclientfiles/onoakcoc/images/85d21586-e9f3-427a-8b2b-6f87f5c3510e.png"
              alt="Every Avenue"
              className="h-8 w-auto object-contain"
            />
            <div>
              <h1 className="text-base font-semibold text-[var(--foreground)]">Every Avenue</h1>
              <p className="text-[10px] text-[var(--muted-foreground)] tracking-wide uppercase">Archives Search</p>
            </div>
          </div>
          {hasResult && (
            <Button
              onClick={handleReset}
              variant="ghost"
              size="sm"
              className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              ← New Search
            </Button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {/* Idle State - Centered hero */}
        {isIdle && (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 animate-fade-in">
            <div className="w-full max-w-xl text-center space-y-8">
              {/* Logo */}
              <img
                src="https://widgets.oakvillechamber.com/feeds/membershipclientfiles/onoakcoc/images/85d21586-e9f3-427a-8b2b-6f87f5c3510e.png"
                alt="Every Avenue"
                className="h-16 w-auto object-contain mx-auto opacity-80"
              />

              {/* Title */}
              <div className="space-y-2">
                <h2 className="text-2xl md:text-3xl font-light text-[var(--foreground)]">
                  What would you like to know?
                </h2>
                <p className="text-sm text-[var(--muted-foreground)]">
                  Search through archived conversations and documents
                </p>
              </div>

              {/* Search Input */}
              <form onSubmit={handleSubmit} className="w-full">
                <div className="flex gap-2">
                  <Input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Ask anything..."
                    className="flex-1 h-12 px-4 text-base rounded-xl border-[var(--border)] focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)]"
                    autoFocus
                  />
                  <Button
                    type="submit"
                    disabled={!inputValue.trim()}
                    className="h-12 px-6 rounded-xl"
                  >
                    Search
                  </Button>
                </div>
              </form>

              {/* Suggestions */}
              <div className="flex flex-wrap gap-2 justify-center">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="text-sm px-4 py-2 rounded-full bg-[var(--muted)] text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex-1 flex flex-col px-4 py-6 max-w-3xl mx-auto w-full animate-fade-in">
            {/* Query Display */}
            <div className="mb-6 p-4 rounded-xl bg-[var(--muted)]">
              <p className="text-sm text-[var(--muted-foreground)] mb-1">Searching for:</p>
              <p className="text-[var(--foreground)] font-medium">{state.query}</p>
            </div>

            {/* Loading Animation */}
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-4">
                <div className="flex justify-center gap-1">
                  <span className="w-2 h-2 bg-[var(--primary)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-[var(--primary)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-[var(--primary)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <p className="text-sm text-[var(--muted-foreground)]">Searching archives...</p>
              </div>
            </div>
          </div>
        )}

        {/* Success State - Answer */}
        {state.status === 'success' && (
          <div className="flex-1 px-4 py-6 max-w-3xl mx-auto w-full animate-fade-in">
            {/* Query Display */}
            <div className="mb-6 p-4 rounded-xl bg-[var(--muted)]">
              <p className="text-sm text-[var(--muted-foreground)] mb-1">You asked:</p>
              <p className="text-[var(--foreground)] font-medium">{state.query}</p>
            </div>

            {/* Answer Card */}
            <Card className="mb-6">
              <CardHeader className="pb-2">
                <CardDescription>
                  Based on {state.retrievalCount} archived conversations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-[var(--foreground)] prose-p:text-[var(--foreground)] prose-strong:text-[var(--foreground)] prose-ul:text-[var(--foreground)] prose-ol:text-[var(--foreground)] prose-li:text-[var(--foreground)]">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      h1: ({ children }) => <h1 className="text-xl font-bold mb-4 mt-6 first:mt-0">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-lg font-semibold mb-3 mt-5">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-base font-semibold mb-2 mt-4">{children}</h3>,
                      p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
                      ul: ({ children }) => <ul className="list-disc list-outside ml-4 mb-3 space-y-1">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-outside ml-4 mb-3 space-y-1">{children}</ol>,
                      li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                      a: ({ href, children }) => (
                        <a href={href} className="text-[var(--primary)] underline hover:opacity-80" target="_blank" rel="noopener noreferrer">
                          {children}
                        </a>
                      ),
                      code: ({ children }) => (
                        <code className="bg-[var(--muted)] px-1.5 py-0.5 rounded text-sm font-mono">{children}</code>
                      ),
                      pre: ({ children }) => (
                        <pre className="bg-[var(--muted)] p-4 rounded-lg overflow-x-auto mb-4">{children}</pre>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-[var(--border)] pl-4 italic my-4">{children}</blockquote>
                      ),
                      hr: () => <hr className="my-6 border-[var(--border)]" />,
                      table: ({ children }) => (
                        <div className="overflow-x-auto mb-4">
                          <table className="min-w-full border border-[var(--border)]">{children}</table>
                        </div>
                      ),
                      th: ({ children }) => (
                        <th className="border border-[var(--border)] px-3 py-2 bg-[var(--muted)] font-semibold text-left">{children}</th>
                      ),
                      td: ({ children }) => (
                        <td className="border border-[var(--border)] px-3 py-2">{children}</td>
                      ),
                    }}
                  >
                    {state.answer || ''}
                  </ReactMarkdown>
                </div>
              </CardContent>
            </Card>

            {/* Sources Section */}
            {state.sources.length > 0 && (
              <div className="mb-6">
                <button
                  onClick={() => setSourcesExpanded(!sourcesExpanded)}
                  className="flex items-center gap-2 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
                >
                  <span>📚</span>
                  <span>{state.sources.length} sources</span>
                  <span className="text-xs">{sourcesExpanded ? '▼' : '▶'}</span>
                </button>

                {sourcesExpanded && (
                  <div className="mt-3 space-y-2 animate-fade-in">
                    {state.sources.map((source, index) => (
                      <div
                        key={index}
                        className="p-3 rounded-lg bg-[var(--muted)] text-sm"
                      >
                        <span className="font-medium">{source.channel}</span>
                        <span className="text-[var(--muted-foreground)]"> · {source.date}</span>
                        <span className="text-[var(--muted-foreground)]"> · {source.message_count} messages</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Ask Another Button */}
            <div className="text-center">
              <Button
                onClick={handleReset}
                variant="outline"
                size="lg"
                className="rounded-xl"
              >
                ↺ Ask Another Question
              </Button>
            </div>
          </div>
        )}

        {/* Error State */}
        {state.status === 'error' && (
          <div className="flex-1 px-4 py-6 max-w-3xl mx-auto w-full animate-fade-in">
            {/* Query Display */}
            <div className="mb-6 p-4 rounded-xl bg-[var(--muted)]">
              <p className="text-sm text-[var(--muted-foreground)] mb-1">You asked:</p>
              <p className="text-[var(--foreground)] font-medium">{state.query}</p>
            </div>

            {/* Error Card */}
            <Card className="mb-6 border-red-200 dark:border-red-900">
              <CardContent className="pt-6">
                <div className="text-center space-y-4">
                  <div className="text-4xl">⚠️</div>
                  <p className="text-[var(--foreground)]">Something went wrong</p>
                  <p className="text-sm text-[var(--muted-foreground)]">{state.error}</p>
                </div>
              </CardContent>
            </Card>

            {/* Retry Button */}
            <div className="text-center space-x-3">
              <Button
                onClick={() => {
                  setInputValue(state.query);
                  handleReset();
                }}
                variant="outline"
                size="lg"
                className="rounded-xl"
              >
                Try Again
              </Button>
              <Button
                onClick={handleReset}
                variant="ghost"
                size="lg"
                className="rounded-xl"
              >
                New Search
              </Button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="flex-shrink-0 py-4 text-center safe-bottom">
        <p className="text-xs text-[var(--muted-foreground)]">
          Powered by Every Avenue Archives
        </p>
      </footer>
    </div>
  );
}
