-- Materialized views exported from prod www (pg_get_viewdef + pg_indexes).
-- Re-export when a migration changes a view. Order matters: mv_category reads mv_video.

CREATE MATERIALIZED VIEW mv_video AS
 SELECT entity.id,
    entity.prev,
    entity.extractor_data,
    entity.allow,
    entity.rating,
    entity.published,
    entity.title,
    entity.thumbnail,
    entity.thumbnail_ac,
    entity.yt_views,
    entity.duration,
    entity.description,
    entity.category,
    entity.tags,
    entity.exists_ia,
    entity.restricted_ia,
    entity.exists_ac,
    entity.ac_views,
    entity.videofile,
    entity.dark_ia,
    entity.loggedin_ia,
    entity.novideo_ia,
    entity.yt_deleted_date,
    source.ytc_title,
    source.ytc_id,
    (setweight(to_tsvector((COALESCE(entity.extractor_data, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(entity.title, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(entity.description, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(entity.category, ''::character varying))::text), 'D'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_title, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_id, ''::character varying))::text), 'D'::"char") || setweight(to_tsvector((COALESCE(entity.tags, ''::character varying))::text), 'D'::"char"))))))) AS document
   FROM ((entity
     JOIN content ON ((content.video_id = entity.id)))
     JOIN source ON ((source.id = content.source_id)))
  WHERE ((entity.yt_deleted OR entity.yt_limited) AND (entity.exists_ac OR (entity.exists_ia AND (NOT COALESCE(entity.novideo_ia, false)))) AND entity.allow)
  GROUP BY entity.id, source.ytc_title, source.ytc_id
  ORDER BY entity.id DESC
WITH NO DATA;
CREATE UNIQUE INDEX mv_video_unique_idx ON public.mv_video USING btree (id, ytc_id);
CREATE INDEX mv_video_gin_idx ON public.mv_video USING gin (document);

CREATE MATERIALIZED VIEW mv_altcen_user AS
 SELECT id,
    username,
    description,
    view_counter,
    featured_playlist,
    public,
    (setweight(to_tsvector(COALESCE(username, (''::character varying)::text)), 'A'::"char") || setweight(to_tsvector(COALESCE(description, (''::character varying)::text)), 'A'::"char")) AS document
   FROM altcen_user
  ORDER BY id DESC
WITH NO DATA;
CREATE INDEX mv_altcen_user_gin_idx ON public.mv_altcen_user USING gin (document);
CREATE UNIQUE INDEX mv_altcen_user_unique_idx ON public.mv_altcen_user USING btree (id, username);

CREATE MATERIALIZED VIEW mv_category AS
 SELECT category.cat_id,
    category.cat_name,
    category.cat_image,
    count(mv_video.category) AS cat_count
   FROM (mv_video
     JOIN category ON (((category.cat_name)::text = (mv_video.category)::text)))
  GROUP BY category.cat_id, category.cat_name, category.cat_image
  ORDER BY (count(mv_video.category)) DESC
WITH NO DATA;
CREATE UNIQUE INDEX mv_category_unique_idx ON public.mv_category USING btree (cat_id);

CREATE MATERIALIZED VIEW mv_channel AS
 SELECT source.id,
    source.ytc_id,
    source.url,
    source.ytc_title,
    source.ytc_publishedat,
    source.ytc_thumbnail,
    source.ytc_thumbnailurl,
    source.ytc_viewcount,
    source.ytc_subscribercount,
    source.ytc_description,
    source.ytc_customurl,
    source.ytc_deleted,
    source.ytc_archive,
    source.ytc_deleteddate,
    source.ytc_addeddate,
    source.ytc_partarchive,
    source.ytc_latestarchive,
    source.delta,
    source.was_full,
    source.was_part,
    source.ytc_moddate,
    source.ytc_videocount,
    max(entity.published) AS newest_video,
    ( SELECT entity_1.allow
           FROM entity entity_1
          WHERE (source.id = entity_1.id)) AS allow,
    count(source.id) AS total,
    count(source.id) FILTER (WHERE ((entity.yt_deleted OR entity.yt_limited) AND (entity.exists_ia OR entity.exists_ac) AND entity.allow)) AS limited,
    count(source.id) FILTER (WHERE ((entity.exists_ia OR entity.exists_ac) AND entity.allow)) AS archived,
    (setweight(to_tsvector((COALESCE(source.ytc_id, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_title, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_description, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(source.ytc_customurl, ''::character varying))::text), 'A'::"char")))) AS document
   FROM ((entity
     JOIN content ON ((content.video_id = entity.id)))
     JOIN source ON ((source.id = content.source_id)))
  GROUP BY source.id
 HAVING (count(source.id) > 0)
  ORDER BY source.id DESC
WITH NO DATA;
CREATE UNIQUE INDEX mv_channel_unique_idx ON public.mv_channel USING btree (id);
CREATE INDEX channel_document_gin_idx2 ON public.mv_channel USING gin (document);

CREATE MATERIALIZED VIEW mv_playlist AS
 SELECT id,
    hashid,
    title,
    user_id,
    description,
    videos,
    video_count,
    view_counter,
    created,
    updated,
    public,
    featured_video,
    featured_video_id,
    (setweight(to_tsvector((COALESCE(hashid, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector(COALESCE(title, (''::character varying)::text)), 'A'::"char") || setweight(to_tsvector(COALESCE(description, (''::character varying)::text)), 'A'::"char"))) AS document
   FROM playlist
  ORDER BY id DESC
WITH NO DATA;
CREATE INDEX mv_playlist_gin_idx ON public.mv_playlist USING gin (document);
CREATE UNIQUE INDEX mv_playlist_id_idx ON public.mv_playlist USING btree (id, hashid);
