CREATE TABLE IF NOT EXISTS public.translation
(
    varname TEXT PRIMARY KEY,
    en TEXT NOT NULL,
    de TEXT,
    es TEXT,
    fr TEXT,
    pt TEXT,
    nl TEXT,
    it TEXT,
    se TEXT,
    CONSTRAINT varname_key UNIQUE (varname)
);

CREATE UNIQUE INDEX varname_unique_idx
  ON public.translation
  USING btree
  (lower(varname) COLLATE pg_catalog."default");
