CREATE TABLE IF NOT EXISTS public.vpn_node (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    fqdn TEXT NOT NULL,
    wg_publickey TEXT NOT NULL,
    wg_privatekey TEXT NOT NULL,
    wg_sharedkey TEXT NOT NULL,
    api_authkey = TEXT NOT NULL,
    api_port = INTEGER NOT NULL,
    wg_port = INTEGER NOT NULL,
    bwLimit INTEGER NOT NULL DEFAULT 1000,
    subExpiry_days INTEGER NOT NULL DEFAULT 30
);