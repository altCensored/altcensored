CREATE TABLE IF NOT EXISTS public.altcen_user (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    email_verified BOOL NOT NULL DEFAULT FALSE,
    password TEXT NOT NULL,
    watched INT[],
    created_date timestamptz,
    email_verified_date timestamptz,
    updated timestamptz,
    locale TEXT,
    theme TEXT,
    navtabs TEXT[],
    navtabs_index TEXT[],
    username TEXT,
    description TEXT,
    view_counter integer,
    featured_video integer,
    featured_playlist integer,
    public BOOL NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.altcen_user_subscription (
    user_id INT REFERENCES public.altcen_user(id),
    ytc_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.playlist
(
    title text,
    id VARCHAR primary key,
    user_id INT REFERENCES public.altcen_user(id) ON DELETE CASCADE NOT NULL,
    description text,
    videos INT[],
    video_count integer,
    view_counter integer,
    created timestamptz,
    updated timestamptz,
    public BOOL NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS playlist_id_idx ON public.playlist(id);

