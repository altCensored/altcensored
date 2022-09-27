CREATE TABLE IF NOT EXISTS public.vpn_node (
    name TEXT  PRIMARY KEY,
    fqdn TEXT NOT NULL,
    publickey TEXT NOT NULL,
    privatekey  TEXT NOT NULL,
    ipaddress TEXT NOT NULL,
    dns_ipaddress TEXT NOT NULL,
    free BOOL NOT NULL DEFAULT FALSE
);