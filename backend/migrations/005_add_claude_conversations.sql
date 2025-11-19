-- Migration: Add Claude AI conversation history tables
-- Created: 2025-11-19
-- Description: Store Claude AI conversations and messages for history/replay

-- Conversations table (chat sessions)
CREATE TABLE IF NOT EXISTS claude_conversations (
    conversation_id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_created ON claude_conversations(created_at DESC);
CREATE INDEX idx_conversations_updated ON claude_conversations(updated_at DESC);

-- Messages table (individual messages in conversations)
CREATE TABLE IF NOT EXISTS claude_messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES claude_conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    usage JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON claude_messages(conversation_id, created_at);
CREATE INDEX idx_messages_created ON claude_messages(created_at DESC);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE claude_conversations
    SET updated_at = NOW()
    WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update conversation timestamp when new message added
CREATE TRIGGER trigger_update_conversation_timestamp
    AFTER INSERT ON claude_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamp();

-- Add comment
COMMENT ON TABLE claude_conversations IS 'Stores Claude AI chat conversation sessions';
COMMENT ON TABLE claude_messages IS 'Stores individual messages within Claude AI conversations';
