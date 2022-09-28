CREATE TABLE IF NOT EXISTS public.vpn_conn (
    id SERIAL PRIMARY KEY,
    publickey TEXT UNIQUE NOT NULL,
    vpn_node_name TEXT REFERENCES vpn_node (name) NOT NULL,
    altcen_user_id INTEGER REFERENCES altcen_user (id) NOT NULL,
    privatekey TEXT UNIQUE NOT NULL,
    sharedkey TEXT UNIQUE NOT NULL,
    key_id INTEGER,
    bw_limit INTEGER,
    bw_used INTEGER NOT NULL DEFAULT 0,
    sub_expiry TEXT,
    expired BOOL NOT NULL DEFAULT FALSE,
    created timestamptz,
    allowedIPs TEXT,
    dns TEXT,
    ipAddress TEXT,
    ipv4Address TEXT,
    ipv6Address TEXT
);