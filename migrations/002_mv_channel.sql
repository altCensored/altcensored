SELECT source.id,
    source.ytc_id,
    source.url,
    source.ytc_title,
    source.ytc_publishedat,
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
    ( SELECT entity_1.allow
           FROM entity entity_1
          WHERE (source.id = entity_1.id)) AS allow,
    count(source.id) AS total,
    count(source.id) FILTER (WHERE (((entity.likes = 0) AND (entity.dislikes = 0) AND (entity.views = 0) AND (entity.yt_views <> 0)) OR (entity.allow AND entity.yt_deleted AND entity.exists_ia AND (entity.yt_views <> 0)))) AS limited,
    (setweight(to_tsvector((COALESCE(source.ytc_id, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_title, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_description, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(source.ytc_customurl, ''::character varying))::text), 'A'::"char")))) AS document
   FROM ((entity
     JOIN content ON ((content.video_id = entity.id)))
     JOIN source ON ((source.id = content.source_id)))
  GROUP BY source.id, entity.allow
 HAVING (count(source.id) > 0)
  ORDER BY source.id DESC