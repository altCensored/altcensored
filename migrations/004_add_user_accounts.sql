CREATE TABLE IF NOT EXISTS "altcen_user" (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    email_verified BOOL NOT NULL DEFAULT FALSE,
    password TEXT NOT NULL,
    watched INT[],
    created_date timestamptz,
    email_verified_date timestamptz,
    updated timestamptz,
    preferences TEXT[]
);

CREATE TABLE IF NOT EXISTS altcen_user_subscription (
    user_id INT REFERENCES "altcen_user"(id),
    ytc_id TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS altcen_user_view (
    user_id INT REFERENCES "altcen_user"(id) ON DELETE CASCADE,
    video_id INT REFERENCES entity(id) ON DELETE CASCADE,
    view_time TIMESTAMP DEFAULT NOW()
);


CREATE INDEX IF NOT EXISTS altcen_user_view_user_id_idx ON altcen_user_view(user_id);
