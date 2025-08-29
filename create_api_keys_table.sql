-- Create API keys table for developer access
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    rate_limit INTEGER DEFAULT 1000, -- requests per hour
    metadata JSONB DEFAULT '{}',
    CONSTRAINT unique_email_name UNIQUE(email, name)
);

-- Index for fast key lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_api_keys_email ON api_keys(email);

-- Sample data for testing
INSERT INTO api_keys (key, name, email) 
VALUES ('nwsl-demo-key-2024', 'Demo Key', 'demo@nwsl-api.com')
ON CONFLICT (key) DO NOTHING;