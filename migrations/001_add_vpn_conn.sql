CREATE TABLE IF NOT EXISTS public.vpn_conn (
    publickey TEXT,
    vpn_node_name TEXT REFERENCES vpn_node (name),
    altcen_user_id INTEGER REFERENCES altcen_user (id) NOT NULL,
    PRIMARY KEY (publickey, vpn_node_name),
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