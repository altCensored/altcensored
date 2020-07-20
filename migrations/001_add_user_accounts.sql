CREATE TABLE "public.user" (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    email_verified BOOL NOT NULL DEFAULT FALSE,
    password TEXT NOT NULL
);

CREATE TABLE user_subscription (
    user_id INT REFERENCES "public.user"(id),
    ytc_id TEXT NOT NULL
);

CREATE TABLE user_view (
    user_id INT REFERENCES "public.user"(id),
    video_id INT REFERENCES entity(id)
);