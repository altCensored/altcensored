CREATE TABLE IF NOT EXISTS public.email_list (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    username TEXT NOT NULL,
    firstname TEXT,
    lastname TEXT,
    email_source TEXT NOT NULL,
    email_subscribed BOOL NOT NULL DEFAULT TRUE,
    email_action TEXT,
    created_date timestamptz,
    email_lastsent_date timestamptz,
    updated timestamptz
);