-- 1. Create the api_keys table
CREATE TABLE api_keys (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    provider_name TEXT NOT NULL, -- e.g., 'github', 'groq', 'openai'
    api_key_encrypted TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    UNIQUE(user_id, provider_name)
);

-- 2. Enable Row Level Security (RLS)
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- 3. Create Policy: Users can only select their OWN api keys
CREATE POLICY "Users can view their own api keys"
ON api_keys FOR SELECT
USING (auth.uid() = user_id);

-- 4. Create Policy: Users can only insert their OWN api keys
CREATE POLICY "Users can insert their own api keys"
ON api_keys FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- 5. Create Policy: Users can only update their OWN api keys
CREATE POLICY "Users can update their own api keys"
ON api_keys FOR UPDATE
USING (auth.uid() = user_id);

-- 6. Create Policy: Users can only delete their OWN api keys
CREATE POLICY "Users can delete their own api keys"
ON api_keys FOR DELETE
USING (auth.uid() = user_id);
