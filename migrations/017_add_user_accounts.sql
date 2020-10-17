CREATE TABLE IF NOT EXISTS public.altcen_user (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    email_verified BOOL NOT NULL DEFAULT FALSE,
    password TEXT NOT NULL,
    watched TEXT[],
    watchlater TEXT[],
    created_date timestamptz,
    email_verified_date timestamptz,
    updated timestamptz,
    navtabs TEXT[],
    navtabs_index TEXT[],
    username TEXT NOT NULL,
    description TEXT,
    view_counter integer,
    featured_video_old TEXT,
    featured_video JSON,
    featured_playlist VARCHAR,
    settings JSON,
    public BOOL NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.altcen_user_subscription (
    user_id INT REFERENCES public.altcen_user(id),
    ytc_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.playlist
(
    id SERIAL PRIMARY KEY,
    hashid VARCHAR NOT NULL,
    title text,
    user_id INT REFERENCES public.altcen_user(id) ON DELETE CASCADE NOT NULL,
    description text,    
    videos TEXT[],
    video_count integer,
    view_counter integer,
    created timestamptz,
    updated timestamptz,
    public BOOL NOT NULL DEFAULT TRUE,
    featured_video JSON,
    featured BOOL
);

CREATE TABLE IF NOT EXISTS public.counter
(
    hash bigint PRIMARY KEY
);

CREATE INDEX IF NOT EXISTS playlist_id_idx ON public.playlist(id);
