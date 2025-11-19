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
  const [showSidebar, setShowSidebar] = useState(true);
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
    <div className="flex gap-6 h-full">
      {/* Sidebar */}
      {showSidebar && (
        <div className="w-80 flex-shrink-0">
          <div className="card h-[calc(100vh-12rem)] flex flex-col p-0">
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
      )}

      {/* Main chat area */}
      <div className="flex-1 space-y-6">
        {/* Page header */}
        <div>
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-lg flex items-center justify-center">
              <Sparkles className="text-white" size={24} />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900">Claude AI</h1>
              <p className="text-gray-600">
                Ask natural language questions about your poker data
              </p>
            </div>
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="btn-secondary flex items-center gap-2"
            >
              <MessageSquare size={18} />
              {showSidebar ? 'Hide' : 'Show'} History
            </button>
          </div>
        </div>

        {/* Chat container */}
        <div className="card h-[calc(100vh-16rem)] flex flex-col p-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
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
                className={`flex space-x-3 max-w-3xl ${
                  message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                }`}
              >
                {/* Avatar */}
                <div
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    message.role === 'user'
                      ? 'bg-blue-600'
                      : 'bg-gradient-to-br from-purple-600 to-indigo-600'
                  }`}
                >
                  {message.role === 'user' ? (
                    <User size={18} className="text-white" />
                  ) : (
                    <Bot size={18} className="text-white" />
                  )}
                </div>

                {/* Message content */}
                <div
                  className={`flex-1 px-4 py-3 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {message.role === 'user' ? (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
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
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSubmit} className="flex space-x-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Claude about your poker data..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>Send</span>
              <Send size={18} />
            </button>
          </form>
        </div>
        </div>

        {/* Info */}
        <div className="card bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200">
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
