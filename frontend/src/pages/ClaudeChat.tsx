import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Send, Bot, User, Loader, Sparkles, MessageSquare, Trash2, Plus } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { api } from '../services/api';
import type { ClaudeQueryResponse, ConversationListItem } from '../types';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  usage?: { input_tokens: number; output_tokens: number };
}

const ClaudeChat = () => {
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [showSidebar, setShowSidebar] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Pre-populate query if player parameter exists
  useEffect(() => {
    const player = searchParams.get('player');
    if (player && messages.length === 0) {
      setInput(`Analyze ${player} and tell me how to exploit them`);
    }
  }, [searchParams]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversations = async () => {
    try {
      const convos = await api.getConversations(50);
      setConversations(convos);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  };

  const loadConversation = async (convId: number) => {
    try {
      setLoading(true);
      const conversation = await api.getConversation(convId);

      // Convert conversation messages to local Message format
      const loadedMessages: Message[] = conversation.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.created_at),
        usage: msg.usage as any,
      }));

      setMessages(loadedMessages);
      setConversationId(conversation.conversation_id);
      setError(null);
    } catch (err) {
      setError('Failed to load conversation');
    } finally {
      setLoading(false);
    }
  };

  const deleteConversation = async (convId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await api.deleteConversation(convId);
      await loadConversations();

      // If we deleted the current conversation, start a new one
      if (convId === conversationId) {
        startNewConversation();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      // Build conversation history for context
      const conversationHistory = messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      const response: ClaudeQueryResponse = await api.queryClaude({
        query: userMessage.content,
        conversation_history: conversationHistory,
        conversation_id: conversationId || undefined,
      });

      if (response.success) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: response.response,
          timestamp: new Date(),
          usage: response.usage,
        };
        setMessages((prev) => [...prev, assistantMessage]);

        // Save the conversation ID from the response
        if (response.conversation_id && !conversationId) {
          setConversationId(response.conversation_id);
          // Reload conversations to show the new one in the sidebar
          loadConversations();
        }
      } else {
        setError(response.error || 'Failed to get response from Claude');
      }
    } catch (err) {
      setError((err as Error).message || 'Failed to send message');
    } finally {
      setLoading(false);
    }
  };

  const exampleQueries = [
    'Who are the most exploitable players with at least 500 hands?',
    'Show me all TAGs who fold too much under pressure',
    'Which players at NL50 have the worst blind defense?',
    'Find all calling stations with high WTSD%',
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full relative">
      {/* Sidebar - overlay on mobile, sidebar on desktop */}
      {showSidebar && (
        <>
          {/* Backdrop for mobile */}
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
            onClick={() => setShowSidebar(false)}
          />

          {/* Sidebar content */}
          <div className="fixed lg:relative inset-y-0 left-0 z-50 w-80 lg:flex-shrink-0 lg:z-auto">
            <div className="card h-full lg:h-[calc(100vh-12rem)] flex flex-col p-0 m-0 lg:m-0 rounded-none lg:rounded-xl">
            <div className="p-4 border-b border-gray-200">
              <button
                onClick={startNewConversation}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <Plus size={18} />
                New Conversation
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {conversations.map((conv) => (
                <div
                  key={conv.conversation_id}
                  onClick={() => loadConversation(conv.conversation_id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    conv.conversation_id === conversationId
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <MessageSquare size={14} className="text-gray-400 flex-shrink-0" />
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {conv.title}
                        </h4>
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>{conv.message_count} messages</span>
                        <span>{new Date(conv.updated_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => deleteConversation(conv.conversation_id, e)}
                      className="text-gray-400 hover:text-red-600 transition-colors p-1"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}

              {conversations.length === 0 && (
                <div className="text-center py-8 text-sm text-gray-500">
                  No conversations yet.<br />Start chatting to create one!
                </div>
              )}
            </div>
          </div>
        </div>
        </>
      )}

      {/* Main chat area */}
      <div className="flex-1 space-y-6">
        {/* Page header */}
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-lg flex items-center justify-center">
              <Sparkles className="text-white" size={20} />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl sm:text-3xl font-bold text-gray-900">Claude AI</h1>
              <p className="text-sm sm:text-base text-gray-600 hidden sm:block">
                Ask natural language questions about your poker data
              </p>
            </div>
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="btn-secondary flex items-center gap-2 flex-shrink-0"
            >
              <MessageSquare size={18} />
              <span className="hidden sm:inline">{showSidebar ? 'Hide' : 'Show'} History</span>
              <span className="sm:hidden">History</span>
            </button>
          </div>
        </div>

        {/* Chat container */}
        <div className="card h-[calc(100vh-20rem)] sm:h-[calc(100vh-16rem)] flex flex-col p-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Bot size={48} className="mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Welcome to Claude AI Analysis
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Ask me anything about your poker database. I can analyze player tendencies,
                find exploitable opponents, and provide strategic recommendations.
              </p>

              <div className="max-w-2xl mx-auto">
                <p className="text-sm font-medium text-gray-700 mb-3">Example queries:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {exampleQueries.map((query, index) => (
                    <button
                      key={index}
                      onClick={() => setInput(query)}
                      className="text-left p-3 text-sm bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex space-x-2 sm:space-x-3 max-w-full sm:max-w-3xl ${
                  message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                }`}
              >
                {/* Avatar */}
                <div
                  className={`flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user'
                      ? 'bg-blue-600'
                      : 'bg-gradient-to-br from-purple-600 to-indigo-600'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User size={16} className="text-white sm:w-[18px] sm:h-[18px]" />
                  ) : (
                    <Bot size={16} className="text-white sm:w-[18px] sm:h-[18px]" />
                  )}
                </div>

                {/* Message content */}
                <div
                  className={`flex-1 px-3 py-2 sm:px-4 sm:py-3 rounded-lg text-sm sm:text-base ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.role === 'user' ? (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-headings:font-semibold prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-p:text-gray-700 prose-p:leading-relaxed prose-strong:text-gray-900 prose-strong:font-semibold prose-ul:list-disc prose-ol:list-decimal prose-li:text-gray-700 prose-code:text-purple-600 prose-code:bg-purple-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-xs prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:text-gray-700">
                      <ReactMarkdown
                        components={{
                          table: ({ node, ...props }) => (
                            <div className="overflow-x-auto my-4">
                              <table className="min-w-full divide-y divide-gray-300 border border-gray-300 rounded-lg" {...props} />
                            </div>
                          ),
                          thead: ({ node, ...props }) => (
                            <thead className="bg-gray-50" {...props} />
                          ),
                          tbody: ({ node, ...props }) => (
                            <tbody className="divide-y divide-gray-200 bg-white" {...props} />
                          ),
                          tr: ({ node, ...props }) => (
                            <tr className="hover:bg-gray-50" {...props} />
                          ),
                          th: ({ node, ...props }) => (
                            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-900 border-r border-gray-300 last:border-r-0" {...props} />
                          ),
                          td: ({ node, ...props }) => (
                            <td className="px-3 py-2 text-sm text-gray-700 border-r border-gray-200 last:border-r-0" {...props} />
                          ),
                          ul: ({ node, ...props }) => (
                            <ul className="space-y-1 my-3" {...props} />
                          ),
                          ol: ({ node, ...props }) => (
                            <ol className="space-y-1 my-3" {...props} />
                          ),
                          li: ({ node, ...props }) => (
                            <li className="ml-4" {...props} />
                          ),
                          code: ({ node, inline, ...props }: any) => {
                            if (inline) {
                              return <code className="text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded font-mono text-xs" {...props} />;
                            }
                            return (
                              <code className="block bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto text-xs font-mono my-3" {...props} />
                            );
                          },
                          h1: ({ node, ...props }) => (
                            <h1 className="text-xl font-semibold text-gray-900 mt-4 mb-2 pb-2 border-b-2 border-blue-500" {...props} />
                          ),
                          h2: ({ node, ...props }) => (
                            <h2 className="text-lg font-semibold text-gray-900 mt-4 mb-2 pb-1 border-b border-gray-300" {...props} />
                          ),
                          h3: ({ node, ...props }) => (
                            <h3 className="text-base font-semibold text-gray-900 mt-3 mb-2" {...props} />
                          ),
                          blockquote: ({ node, ...props }) => (
                            <blockquote className="border-l-4 border-blue-500 bg-blue-50 pl-4 py-2 my-3 italic text-gray-700" {...props} />
                          ),
                          hr: ({ node, ...props }) => (
                            <hr className="my-4 border-t-2 border-gray-200" {...props} />
                          ),
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* Token usage for assistant messages */}
                  {message.role === 'assistant' && message.usage && (
                    <div className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-500">
                      Tokens: {message.usage.input_tokens} in / {message.usage.output_tokens} out
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex space-x-3 max-w-3xl">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center">
                  <Bot size={18} className="text-white" />
                </div>
                <div className="flex-1 px-4 py-3 rounded-lg bg-gray-100">
                  <div className="flex items-center space-x-2">
                    <Loader size={18} className="animate-spin text-gray-600" />
                    <span className="text-sm text-gray-600">Claude is thinking...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input form */}
        <div className="border-t border-gray-200 p-3 sm:p-4">
          <form onSubmit={handleSubmit} className="flex space-x-2 sm:space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Claude..."
              className="flex-1 px-3 py-2 sm:px-4 sm:py-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="btn-primary flex items-center space-x-2 px-4 sm:px-6 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="hidden sm:inline">Send</span>
              <Send size={18} />
            </button>
          </form>
        </div>
        </div>

        {/* Info */}
        <div className="card bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200 hidden lg:block">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">How Claude Works</h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start">
              <span className="text-purple-600 mr-2">•</span>
              <span>Claude has direct access to your PostgreSQL database via SQL queries</span>
            </li>
            <li className="flex items-start">
              <span className="text-purple-600 mr-2">•</span>
              <span>Ask questions in natural language - Claude will figure out what data to query</span>
            </li>
            <li className="flex items-start">
              <span className="text-purple-600 mr-2">•</span>
              <span>Claude understands all 12 composite metrics and player type classifications</span>
            </li>
            <li className="flex items-start">
              <span className="text-purple-600 mr-2">•</span>
              <span>Receives strategic recommendations based on exploitative poker theory</span>
            </li>
            <li className="flex items-start">
              <span className="text-purple-600 mr-2">•</span>
              <span>Conversation history is maintained for follow-up questions and saved for later</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ClaudeChat;
