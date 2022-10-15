CREATE TABLE IF NOT EXISTS public.crypto (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    tag TEXT NOT NULL,
    address TEXT NOT NULL
);