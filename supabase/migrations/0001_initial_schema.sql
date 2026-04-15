-- 0001_initial_schema.sql
-- Hunter Ghost Creator Multi-Tenant Schema

-- 1. Profiles (Extends Auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. User Settings (Encapsulates all config)
CREATE TABLE IF NOT EXISTS public.user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    api_keys JSONB DEFAULT '{}'::jsonb,
    tts_settings JSONB DEFAULT '{}'::jsonb,
    image_settings JSONB DEFAULT '{}'::jsonb,
    pipeline_settings JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 3. Video Jobs (Pipeline history)
CREATE TABLE IF NOT EXISTS public.video_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, scripting, voicing, imaging, building, uploading, completed, failed
    video_url TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.video_jobs ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies
-- Profiles: Users can read all profiles but only update their own
CREATE POLICY "Public profiles are viewable by everyone" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- User Settings: Only the owner can see and update their own settings
CREATE POLICY "Users can see own settings" ON public.user_settings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own settings" ON public.user_settings FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own settings" ON public.user_settings FOR UPDATE USING (auth.uid() = user_id);

-- Video Jobs: Only the owner can see and update their jobs
CREATE POLICY "Users can see own jobs" ON public.video_jobs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own jobs" ON public.video_jobs FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own jobs" ON public.video_jobs FOR UPDATE USING (auth.uid() = user_id);

-- 6. Trigger for profile creation on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, username, full_name, avatar_url)
    VALUES (new.id, new.raw_user_meta_data->>'username', new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'avatar_url');
    
    INSERT INTO public.user_settings (user_id)
    VALUES (new.id);
    
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
