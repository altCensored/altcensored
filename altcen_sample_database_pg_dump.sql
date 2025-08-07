--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: altcen; Type: DATABASE; Schema: -; Owner: altcen
--

CREATE DATABASE altcen WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'en_US.UTF-8';


ALTER DATABASE altcen OWNER TO altcen;

\connect altcen

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: altcen_user; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.altcen_user (
    id integer NOT NULL,
    email character varying NOT NULL,
    email_verified boolean NOT NULL,
    email_subscribed boolean NOT NULL,
    email_action character varying,
    password character varying,
    watched character varying[],
    watchlater character varying[],
    created_date timestamp without time zone,
    email_verified_date timestamp without time zone,
    email_lastsent_date timestamp without time zone,
    updated timestamp without time zone,
    navtabs character varying[],
    navtabs_index character varying[],
    username character varying,
    description character varying,
    public boolean NOT NULL,
    view_counter integer,
    contributor boolean NOT NULL,
    settings json,
    featured_playlist json
);


ALTER TABLE public.altcen_user OWNER TO altcen;

--
-- Name: altcen_user_id_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.altcen_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.altcen_user_id_seq OWNER TO altcen;

--
-- Name: altcen_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.altcen_user_id_seq OWNED BY public.altcen_user.id;


--
-- Name: category; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.category (
    cat_id integer NOT NULL,
    cat_name character varying NOT NULL,
    cat_image character varying NOT NULL
);


ALTER TABLE public.category OWNER TO altcen;

--
-- Name: category_cat_id_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.category_cat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.category_cat_id_seq OWNER TO altcen;

--
-- Name: category_cat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.category_cat_id_seq OWNED BY public.category.cat_id;


--
-- Name: config; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.config (
    id character varying NOT NULL,
    value character varying
);


ALTER TABLE public.config OWNER TO altcen;

--
-- Name: content; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.content (
    source_id integer,
    video_id integer
);


ALTER TABLE public.content OWNER TO altcen;

--
-- Name: counter; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.counter (
    hash bigint NOT NULL
);


ALTER TABLE public.counter OWNER TO altcen;

--
-- Name: counter_hash_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.counter_hash_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.counter_hash_seq OWNER TO altcen;

--
-- Name: counter_hash_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.counter_hash_seq OWNED BY public.counter.hash;


--
-- Name: crypto; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.crypto (
    id integer NOT NULL,
    name character varying NOT NULL,
    tag character varying NOT NULL,
    address character varying NOT NULL
);


ALTER TABLE public.crypto OWNER TO altcen;

--
-- Name: crypto_id_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.crypto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crypto_id_seq OWNER TO altcen;

--
-- Name: crypto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.crypto_id_seq OWNED BY public.crypto.id;


--
-- Name: email_list; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.email_list (
    id integer NOT NULL,
    email character varying NOT NULL,
    username character varying,
    firstname character varying,
    lastname character varying,
    email_source character varying NOT NULL,
    email_subscribed boolean NOT NULL,
    email_action character varying,
    created_date timestamp without time zone,
    email_lastsent_date timestamp without time zone,
    updated timestamp without time zone
);


ALTER TABLE public.email_list OWNER TO altcen;

--
-- Name: email_list_id_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.email_list_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.email_list_id_seq OWNER TO altcen;

--
-- Name: email_list_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.email_list_id_seq OWNED BY public.email_list.id;


--
-- Name: entity; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.entity (
    id integer NOT NULL,
    type character varying NOT NULL,
    prev timestamp without time zone,
    extractor_key character varying NOT NULL,
    extractor_data character varying NOT NULL,
    allow boolean NOT NULL,
    title character varying,
    views integer,
    likes integer,
    dislikes integer,
    yt_comments integer,
    yt_views integer,
    yt_dislikes integer,
    yt_likes integer,
    published timestamp without time zone,
    description character varying,
    tags character varying,
    category character varying,
    rating integer,
    thumbnail character varying,
    thumbnail_ac character varying,
    yt_error_message character varying,
    duration integer,
    sync_ia boolean,
    exists_ia boolean,
    yt_deleted boolean,
    sync_iadate timestamp without time zone,
    addeddate timestamp without time zone,
    filesize_approx integer,
    live_status character varying,
    restricted_ia boolean,
    loggedin_ia boolean,
    uploaderother_ia boolean,
    exists_ac boolean,
    dark_ia boolean,
    exists_ac_mkv boolean,
    found boolean,
    yt_limited boolean,
    ac_views integer,
    videofile character varying,
    novideo_ia boolean
);


ALTER TABLE public.entity OWNER TO altcen;

--
-- Name: entity_id_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.entity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.entity_id_seq OWNER TO altcen;

--
-- Name: entity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.entity_id_seq OWNED BY public.entity.id;


--
-- Name: ia_upload_log; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.ia_upload_log (
    date timestamp without time zone NOT NULL,
    extractor_id character varying NOT NULL,
    log_code character varying,
    ip_add character varying,
    hostname character varying,
    job character varying,
    "user" character varying,
    proxy character varying,
    log_full character varying
);


ALTER TABLE public.ia_upload_log OWNER TO altcen;

--
-- Name: language; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.language (
    lang_id integer NOT NULL,
    lang_name character varying NOT NULL,
    lang_image character varying NOT NULL,
    lang_tagstring character varying NOT NULL,
    lang_code character varying NOT NULL,
    lang_image_css character varying NOT NULL
);


ALTER TABLE public.language OWNER TO altcen;

--
-- Name: language_lang_id_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.language_lang_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.language_lang_id_seq OWNER TO altcen;

--
-- Name: language_lang_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.language_lang_id_seq OWNED BY public.language.lang_id;


--
-- Name: mv_altcen_user; Type: MATERIALIZED VIEW; Schema: public; Owner: altcen
--

CREATE MATERIALIZED VIEW public.mv_altcen_user AS
 SELECT id,
    username,
    description,
    view_counter,
    featured_playlist,
    public,
    (setweight(to_tsvector((COALESCE(username, ((''::character varying)::text)::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(description, ((''::character varying)::text)::character varying))::text), 'A'::"char")) AS document
   FROM public.altcen_user
  ORDER BY id DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_altcen_user OWNER TO altcen;

--
-- Name: playlist; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.playlist (
    id integer NOT NULL,
    hashid character varying NOT NULL,
    title character varying,
    description character varying,
    videos character varying[],
    video_count integer,
    created timestamp with time zone,
    updated timestamp with time zone,
    public boolean NOT NULL,
    view_counter integer,
    user_id integer NOT NULL,
    featured_video json
);


ALTER TABLE public.playlist OWNER TO altcen;

--
-- Name: mv_playlist; Type: MATERIALIZED VIEW; Schema: public; Owner: altcen
--

CREATE MATERIALIZED VIEW public.mv_playlist AS
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
    (setweight(to_tsvector((COALESCE(hashid, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector((COALESCE(title, ((''::character varying)::text)::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(description, ((''::character varying)::text)::character varying))::text), 'A'::"char"))) AS document
   FROM public.playlist
  ORDER BY id DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_playlist OWNER TO altcen;

--
-- Name: playlist_id_seq; Type: SEQUENCE; Schema: public; Owner: altcen
--

CREATE SEQUENCE public.playlist_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.playlist_id_seq OWNER TO altcen;

--
-- Name: playlist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altcen
--

ALTER SEQUENCE public.playlist_id_seq OWNED BY public.playlist.id;


--
-- Name: source; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.source (
    id integer NOT NULL,
    next timestamp without time zone NOT NULL,
    delta interval NOT NULL,
    url character varying NOT NULL,
    extractor_match character varying NOT NULL,
    source_name character varying,
    ytc_etag character varying,
    ytc_id character varying,
    ytc_title character varying,
    ytc_description character varying,
    ytc_customurl character varying,
    ytc_publishedat timestamp without time zone,
    ytc_thumbnailurl character varying,
    ytc_viewcount integer,
    ytc_subscribercount integer,
    ytc_videocount integer,
    ytc_archive boolean NOT NULL,
    ytc_deleted boolean NOT NULL,
    ytc_deleteddate timestamp without time zone,
    ytc_addeddate timestamp without time zone,
    ytc_partarchive boolean NOT NULL,
    ytc_latestarchive boolean NOT NULL,
    next_resync timestamp without time zone,
    s3_ia boolean NOT NULL,
    s3_ac boolean NOT NULL,
    s3_mirror boolean NOT NULL,
    was_full boolean NOT NULL,
    was_part boolean NOT NULL,
    ytc_thumbnail character varying,
    ytc_moddate timestamp without time zone
);


ALTER TABLE public.source OWNER TO altcen;

--
-- Name: translation; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.translation (
    varname character varying NOT NULL,
    en character varying NOT NULL,
    de character varying,
    es character varying,
    fr character varying,
    pt character varying,
    nl character varying,
    it character varying,
    se character varying
);


ALTER TABLE public.translation OWNER TO altcen;

--
-- Name: video; Type: TABLE; Schema: public; Owner: altcen
--

CREATE TABLE public.video (
    id integer NOT NULL
);


ALTER TABLE public.video OWNER TO altcen;

--
-- Name: altcen_user id; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.altcen_user ALTER COLUMN id SET DEFAULT nextval('public.altcen_user_id_seq'::regclass);


--
-- Name: category cat_id; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.category ALTER COLUMN cat_id SET DEFAULT nextval('public.category_cat_id_seq'::regclass);


--
-- Name: counter hash; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.counter ALTER COLUMN hash SET DEFAULT nextval('public.counter_hash_seq'::regclass);


--
-- Name: crypto id; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.crypto ALTER COLUMN id SET DEFAULT nextval('public.crypto_id_seq'::regclass);


--
-- Name: email_list id; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.email_list ALTER COLUMN id SET DEFAULT nextval('public.email_list_id_seq'::regclass);


--
-- Name: entity id; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.entity ALTER COLUMN id SET DEFAULT nextval('public.entity_id_seq'::regclass);


--
-- Name: language lang_id; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.language ALTER COLUMN lang_id SET DEFAULT nextval('public.language_lang_id_seq'::regclass);


--
-- Name: playlist id; Type: DEFAULT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.playlist ALTER COLUMN id SET DEFAULT nextval('public.playlist_id_seq'::regclass);


--
-- Data for Name: altcen_user; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.altcen_user (id, email, email_verified, email_subscribed, email_action, password, watched, watchlater, created_date, email_verified_date, email_lastsent_date, updated, navtabs, navtabs_index, username, description, public, view_counter, contributor, settings, featured_playlist) FROM stdin;
30	l1@veraza.com	t	t	\N	scrypt:32768:8:1$bJEBpjhcMyR2ps8D$0bb8d7842e56a7f18940990ba011b2cafd7cb77ecfe9355921bc2718eca11ca90b3192eac2763ac2da300f9215af0f2662f641e938b9f2c197e46db781affe91	\N	{239HCMH9ERs}	2025-07-30 19:53:58.623622	2025-07-30 19:54:52.299404	2025-06-30 19:53:58.623682	2025-08-02 17:51:31.210013	{video,channel,playlist}	{video,channel,playlist}	l1		f	1	f	{"theme": "light", "locale": "en", "autoplay": "True", "playnext": "True"}	\N
\.


--
-- Data for Name: category; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.category (cat_id, cat_name, cat_image) FROM stdin;
18	Short Movies	ion-ios-cog
21	Videoblogging	ion-ios-cog
2	Autos & Vehicles	ion-ios-car
10	Music	ion-ios-musical-notes
15	Pets & Animals	ion-ios-paw
17	Sports	ion-ios-tennisball
19	Travel & Events	ion-ios-airplane
20	Gaming	ion-ios-trophy
22	People & Blogs	ion-ios-people
23	Comedy	ion-ios-happy
24	Entertainment	ion-ios-headset
25	News & Politics	ion-ios-megaphone
26	Howto & Style	ion-ios-construct
27	Education	ion-ios-school
28	Science & Technology	ion-ios-flask
29	Nonprofits & Activism	ion-ios-book
1	Film & Animation	ion-ios-videocam
\.


--
-- Data for Name: config; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.config (id, value) FROM stdin;
version	2
ydl_version	2025.05.22.093922
\.


--
-- Data for Name: content; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.content (source_id, video_id) FROM stdin;
33	34
33	35
33	36
33	37
33	38
\.


--
-- Data for Name: counter; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.counter (hash) FROM stdin;
174612450199551359
6797047015135162578
-7922165790895892741
3377676237324756918
-7739234639031425143
-9119443001676886025
3242776775189018605
5283794205935669803
-695977997307432546
2753949887037283625
4505325003179948639
-7955603654763629293
8744162678502474478
-7962398181708472236
8021556400698409833
1008495157225737519
-4456155601013682002
-4124478257797687978
-1360532248292998847
6908744673317773861
-4552294692991171516
-7834474719408535950
-5105406003301621767
3458339753722205013
-1447721825468100435
-9065598047406153010
-3592728742381718600
-104708205985320675
-3257873408895249333
-8675833486928304912
6946550441913712916
8796430163297926682
5245893239314833834
5097940728352368811
-3268007977175592357
4380994765184119414
5729005294085881593
-8701238101600476737
3476969587206985809
7921899244047398246
-918246111081502399
4934986914350594155
2078876622996013618
4683387165163776017
7113767016185565281
-1518102951451481512
5735319230029003463
-3364593604924449822
1143709436191287209
5011493418825451551
-1757229922909489387
8718611559458100319
202783210833433765
-6537765913422683409
2854717462498317473
-9125952568728923854
7394023078320674661
-1496240432387575932
5562474398243571289
8656040796888995336
-940602690233786502
-4221786835867851122
7454609954382398616
4109756983821917513
-2314734628458235026
3131177381334926109
1867676510660191497
2794049785560830247
8664824599520134063
3883737998527524292
-1365598001136400760
8098884179949955397
-5775244429246124429
-5080073438771231058
-6729532104172100608
-4244482592767656557
3921925866242341111
7897358466140883423
1322535106411413156
-10782793632701157
-1005380593449466126
-6121057318597710732
8561841239227562379
-453083243422686009
-6889126435108297183
-8107166956086262348
-4586202460285972785
3994588190237556281
4421582050959017060
3185843853661723838
-885177940036330897
-480995497703623516
-1709157333185934715
-6864325419219110905
-3923464217686196054
-7628036111236514663
5283200551817099042
-2830376624379623032
8998732304001282486
-1140322529137743422
-3367669370138995348
-817190597709091913
-8835755355814500729
-446886812502385503
-8547726212064554914
8518336675071790872
3211479379336811004
-4690337102785194129
551213697167827243
-390397275836899316
-6227431271392958490
6853152898693829804
-3551281402124716742
-6208698066306441535
-6066939652075300884
8996387486396253039
-3326904393498191898
4737110985562417895
1373370957831163046
890949913428975606
-6611848196313068659
-5614974115669306804
-8027066818319950450
3887075519391941364
4017087292936013737
-5874591561080045548
2158042480327922510
-3097700118420172208
4038877839770106028
1331314243603414209
-3984249183639337230
6528882426066848975
-7144384617172693807
6156607133535025947
259289487403174859
1519093801404493772
2051999961836835954
-1598963994654170502
-2837691909597088004
-7779786606178823415
-9053099780451975037
-5297255416823986913
-4515004975270983034
3244107655057135421
-1732630329290040230
5492842544480120544
-494586838619670368
7175081935303172112
-987401981966207934
-5596503581638867535
4465806403661623267
9159522494202381183
-477221373093408925
7960511442826002965
2924209242374114576
2383777630002472741
6205717722332660925
-8040781673818979887
-1331067656771438441
7279770268993177367
8365844843333415526
5293498225800397779
156777319908336307
3671040735244803139
-36006608330139598
-9198321700181672211
-887302556920714045
-2302377070687981325
-592877229872029277
3766586258411138608
2355648070675744950
-6482404460005642858
-1201991668958628744
5509877345962826197
578972541974140853
-5370383343032902138
-6448337610594794210
-4444239184699397865
2920622808610637103
2385948248703613669
1957976922752011301
-7616248396025508028
-180918264783010588
-3630339258204932497
5932048188135852415
1219289463305750570
-4873629664247363707
-1963356414048021939
-5902410858040997742
4168778913427490478
-6091867794633756685
-2443889005220623101
-3831973106123769155
-6935073506534520570
7121745681034047807
5485103526683149216
-4423066788169626813
7097192970160080363
-8044390446351854832
-1985607112208971051
3142419504179190992
-6453947777157457105
-1866889387915252654
6394561347183837050
-4150046666224800799
8402020048655047109
-5506010327478466467
-2605348481420114906
-2090210971803741027
6225165778130817142
1977617644802323123
3298237717314556377
-2308341785232205842
7178134381457233387
-4019240084570836897
-2738444672749897078
390998713083892075
-3425718327050185009
-5880967047787351024
-8338914106128027288
-5918343140625772278
6769128357460183273
-7159363874163299173
1148218977157410130
-8258758160456263057
-3427816241023385881
-8940534925292348791
-6318856768091078962
-788945348682344339
8277999334852866822
-2899766351713369492
3733404198053103254
6685482302324933791
-342137043237003568
-7053012932372521410
-1474918118387572561
-3842233680207519465
3228027194747124196
-6955780879292573035
575126427880351473
7494778776415616969
6277225485679969645
2430050621660398288
932738113448311967
-8285313796964786684
-1983007447374675758
5482256539756240021
-2518729405416565070
3953094147755962433
-7239345723332108717
7194205062064110342
\.


--
-- Data for Name: crypto; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.crypto (id, name, tag, address) FROM stdin;
1	Bitcoin (BTC)	bitcoin	3PRivnBUoVLXHeBQTSP4FNPw5R8b9Gztd7
2	Bitcoin Cash (BCH)	bitcoincash	1HMcyukTbppH5Km5ZkFC8MrMiV9FHvaS47
3	Ethereum (ETH)	ethereum	0x8a4173A910C13F5dF67CBeD2d9066805ed582cc8
4	Litecoin (LTC)	litecoin	M9uui38dkxDGFiXHf6gaJxLVUtkubVzUTg
5	Monero (XMR)	monero	46NAazU6xSdEC3ciR19PFLJ2F9HNiGvLG193XJiegxceEsSUK9FTunNC1fnWw2z3kB7hN3MJhM59NSb5LFxEpxaaNpUpUfL
6	Binance (BNB)	bnb	bnb1qq22r3vcjhmhdm0vqgjnxy9qwwgf5udthcxmxp
7	Ripple (XRP)	ripple	rPQYuRBaE2ZKL6e9TutDxJSu7c7feFndnm
8	DASH	dash	XhNmnLzD2e6cVJoKmFUe97jPY3o9ov9NyE
9	Dogecoin (DOGE)	dogecoin	DFBcgsAbfGDGRt8g9xGUaNG7z49SmHW35q
10	Tether (USDT)	ethereum	0x8a4173A910C13F5dF67CBeD2d9066805ed582cc8
11	USD Coin (USDC)	ethereum	0x8a4173A910C13F5dF67CBeD2d9066805ed582cc8
12	Binance USD (BUSD)	bnb	bnb1qq22r3vcjhmhdm0vqgjnxy9qwwgf5udthcxmxp
13	Basic Attention Token (BAT)	ethereum	0x8a4173A910C13F5dF67CBeD2d9066805ed582cc8
14	Polygon (MATIC)	ethereum	0x8a4173A910C13F5dF67CBeD2d9066805ed582cc8
\.


--
-- Data for Name: email_list; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.email_list (id, email, username, firstname, lastname, email_source, email_subscribed, email_action, created_date, email_lastsent_date, updated) FROM stdin;
\.


--
-- Data for Name: entity; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.entity (id, type, prev, extractor_key, extractor_data, allow, title, views, likes, dislikes, yt_comments, yt_views, yt_dislikes, yt_likes, published, description, tags, category, rating, thumbnail, thumbnail_ac, yt_error_message, duration, sync_ia, exists_ia, yt_deleted, sync_iadate, addeddate, filesize_approx, live_status, restricted_ia, loggedin_ia, uploaderother_ia, exists_ac, dark_ia, exists_ac_mkv, found, yt_limited, ac_views, videofile, novideo_ia) FROM stdin;
34	video	2025-07-01 10:17:20.152036	Youtube	-Dg6hRM0Zfg	t	The Solar Fund Standoff: Following the Money at Trump's Latest Target for Funding Cuts	\N	\N	\N	\N	5	\N	0	2025-04-02 00:00:00	The Trump administration has frozen the $7 billion Solar for All program, sparking lawsuits and political battles. Who was set to benefit from these billions, and why is the funding now on hold? Investigative journalist James Varney joins The Miller Report: Real Clear Journalism to break down the winners, the losers, and the controversy behind this massive green energy push. Varney's full investigation can be found on RealClearInvestigations.		People & Blogs	\N	https://i.ytimg.com/vi/-Dg6hRM0Zfg/maxresdefault.jpg	\N	\N	831	\N	\N	f	\N	2025-07-01 10:17:20.152036	58689215	not_live	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
35	video	2025-07-01 10:17:20.152036	Youtube	ElxA0FNHx7Y	t	An Attack on Free Speech: Censorship in America | The Miller Report: Real Clear Journalism	\N	\N	\N	\N	332	\N	3	2025-03-28 00:00:00	In this episode of The Miller Report: Real Clear Journalism, Maggie Miller examines a Senate Judiciary Subcommittee hearing led this week by Chairman Schmitt, which investigated the role of non-governmental organizations (NGOs) in the suppression of free speech and their role in the "Censorship Industrial Complex"—a system that critics argue restricts open discourse and disproportionately affects certain viewpoints.\n\nMaggie is joined by Mollie Hemingway, Editor-in-Chief of The Federalist, and Ben Weingarten, investigative journalist with RealClearInvestigations, both of whom provided testimony at the hearing. They discuss the tangible impact of censorship on journalism, including advertising blacklists that hinder financial sustainability and the broader implications for press freedom.\n\nThis conversation explores key questions: How has government influence shaped censorship? Are recent shifts in major social media companies signaling genuine change? And what legislative actions can be taken to safeguard free expression?		People & Blogs	\N	https://i.ytimg.com/vi/ElxA0FNHx7Y/maxresdefault.jpg	\N	\N	1128	\N	\N	f	\N	2025-07-01 10:17:20.152036	724448606	not_live	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
36	video	2025-07-01 10:17:20.152036	Youtube	zIgKkGSKcNo	t	Los Angeles on Fire: Uncovering the Hidden Crisis Behind the Flames | The Miller Report	\N	\N	\N	\N	493	\N	1	2025-03-23 00:00:00	In this episode of The Miller Report, we cover the growing crisis in Los Angeles — the devastating link between rising homelessness and the surge in fires across the city. From heartbreaking personal stories to shocking statistics showing the alarming rise in fires connected to homeless encampments, we uncover the truth behind who’s really to blame and why city leaders seem reluctant to act.\n\nReal Clear Investigations’ Ana Kasparian joins to discuss her report that highlights frustrated residents, overworked firefighters, and journalists exposing how city leaders cut emergency services while pouring over $1 billion into homeless programs. \n\nHer full investigative report can be found on RealClearInvestigations.com		People & Blogs	\N	https://i.ytimg.com/vi_webp/zIgKkGSKcNo/maxresdefault.webp	\N	\N	954	\N	\N	f	\N	2025-07-01 10:17:20.152036	126491152	not_live	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
33	source	2025-07-01 16:59:29.87116	YoutubeTab	UUZ5rBfggwiDJP99WygU62Wg	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
37	video	2025-07-01 10:17:20.152036	Youtube	JeScsvWVVsk	t	Can One Judge Block the President? The Battle Over Universal Injunctions | The Miller Report	\N	\N	\N	6	904	\N	10	2025-03-19 00:00:00	In this episode of The Miller Report, we dive into the growing controversy surrounding universal injunctions — court orders from a single federal judge that can block nationwide policies. With the Trump administration now asking the Supreme Court to weigh in, we’ll explore how this legal tool has surged in use, its impact on national security decisions, and the mounting political backlash, including new legislation and judicial impeachment efforts.\n\nRealClearInvestigations’ Ben Weingarten joins us to break down what’s at stake for the balance of power between the courts, Congress, and the presidency — and what this means for the future of executive authority in America.\n\nBen's full report can be found at RealClearInvestigations.com		People & Blogs	\N	JeScsvWVVsk.webp	\N	\N	1398	\N	t	t	\N	2025-07-01 10:17:20.152036	772309591	not_live	\N	\N	\N	\N	\N	\N	\N	\N	10	JeScsvWVVsk	\N
38	video	2025-07-01 10:17:20.152	Youtube	239HCMH9ERs	t	no videofiles	\N	\N	\N	\N	332	\N	\N	2025-03-28 00:00:00	\N	\N	People & Blogs	\N	239HCMH9ERs.webp	\N	\N	831	\N	t	f	\N	2025-07-01 10:19:31.417591	58689215	not_live	\N	\N	\N	\N	\N	\N	\N	\N	19	\N	t
\.


--
-- Data for Name: ia_upload_log; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.ia_upload_log (date, extractor_id, log_code, ip_add, hostname, job, "user", proxy, log_full) FROM stdin;
2025-06-09 09:26:38.487266	sxxdddsaa24	Success	127.0.0.2	lc-IdeaPad-1-15IAU7	sync	bob@blow.com	\N	\N
2025-06-09 09:28:10.939556	12345	Success	127.0.0.2	lc-IdeaPad-1-15IAU7	sync	bob@blow.com	\N	\N
2025-06-16 09:40:25.468528	123456	Success	127.0.0.2	lc-IdeaPad-1-15IAU7	sync	bob@blow.com	\N	\N
2025-06-09 09:25:16.478607	s-Tj5LZmKYI	IAReduceRate	127.0.0.2	lc-IdeaPad-1-15IAU7	sync	bob@blow.com	\N	\N
2025-06-09 09:27:19.894971	sxxdaqwaa24	IAReduceRate	127.0.0.2	lc-IdeaPad-1-15IAU7	sync	bob@blow.com	\N	\N
\.


--
-- Data for Name: language; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.language (lang_id, lang_name, lang_image, lang_tagstring, lang_code, lang_image_css) FROM stdin;
51	Polski	pl.svg	Oficjalny, rasowej,etnicznej,religijnej, totalitarnych, komunizm, nazizm, Informację, politycznych, PL, napisy,cyberwmg, żyd, DavidDukePL2, Wrocław, skier137,Jurczenko	PL	flag-icon-pl
56	Pусский	ru.svg	pусский, еврей, Midgardnews, вячеслав, Михаил, Zilzilya, сионизм, мусульманин, заговора, 'Дэвид Дюк', Мировая, tutserega, xRussianpatriotx, война, rusivanbg, Мыслие, SVETOGOR, alexprimin, САБЛЕЗУБ	RU	flag-icon-ru
53	Italiano	it.svg	ilventodelsud, italiano, antifascisti, CasaPound, Giovani, ZETAZEROALFA, verità, 'max white warrior', ebreo, Eisenherz, ITALICO, truffa	IT	flag-icon-it
57	Svenska	se.svg	svenska, Efraim, Nordiska, Motståndsrörelsen, Sverige, 'Artikel 58', MemetiskMagi	SE	flag-icon-se
54	Deutsch	de.svg	deutsch, Jude, VergessenerRuhm, Luegen,  Endstufe, Volkslehrer, NationaIstattGlobal, OttoVonStrumpf, holymoly0009, Teheran2006, TheSARGON87, Friedrich, Sellner, vulgären	DE	flag-icon-de
52	Português	br.svg	português, brasil, homen, mulher, menino, muçulmano, islamismo, judeu, AlternativaAoDebate, cristãos, Machado, Não, Sentinela, 'David Duke BR', BocataDeRealidad, Ascensão, Campedelli, vanlork, marinho, patriotas, Küster, sociedade,Rox	BR	flag-icon-br
55	Français	fr.svg	français, époque, identité, Juif, génocide, frères, Sarkosy, chambre, peuple, Oui, sioniste, politique, Riposte, animoduzoo, Pittmoh,  EspritDeJusticeFR, 'Hyper Crazy 9', blancs, GBienvu, Sylvainjkd, yanndarcmusic, 'Florian R', Tamazgha, 'Télé NATION', ERTV	FR	flag-icon-fr
50	Español	es.svg	España, Español, verdad, garcia, entrevista, himno, canción, patriótica, dios, paíse, hombre, lucho, judío, zionista, Superioridad, ejercito, chilena, discurso, Patriotica, desierto, Duygu, BuenAyre, Madrid, Hispania, brum, historia, LINZROQUE, mendes, castellano	ES	flag-icon-es
\.


--
-- Data for Name: playlist; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.playlist (id, hashid, title, description, videos, video_count, created, updated, public, view_counter, user_id, featured_video) FROM stdin;
\.


--
-- Data for Name: source; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.source (id, next, delta, url, extractor_match, source_name, ytc_etag, ytc_id, ytc_title, ytc_description, ytc_customurl, ytc_publishedat, ytc_thumbnailurl, ytc_viewcount, ytc_subscribercount, ytc_videocount, ytc_archive, ytc_deleted, ytc_deleteddate, ytc_addeddate, ytc_partarchive, ytc_latestarchive, next_resync, s3_ia, s3_ac, s3_mirror, was_full, was_part, ytc_thumbnail, ytc_moddate) FROM stdin;
33	2025-07-06 16:59:29.87116	5 days	https://www.youtube.com/playlist?list=UUZ5rBfggwiDJP99WygU62Wg	[null, "playlist?list=", "UUZ5rBfggwiDJP99WygU62Wg"]	The Miller Report	-9sI99ZpjxoBxnh4M1uIBeowu9I	UCZ5rBfggwiDJP99WygU62Wg	The Miller Report	At The Miller Report we deliver in-depth, fact-driven reporting on the stories that shape our world. Through thoughtful analysis and exclusive interviews with Real Clear Investigation's lead investigators, we explore complex issues, uncover hidden truths, and provide a clearer understanding of current events and policies.	@themillerreportrci	2025-03-03 20:30:31.110997	https://yt3.ggpht.com/gOVMxz3vyokw-eFVKdtp-o6JPKKML6Nf5amneIfXgyGz7nYZGIhFoQkLcZR3XZ-ZdcqrZ5D2AQ=s88-c-k-c0x00ffffff-no-rj	1734	17	4	f	f	\N	2025-07-01 10:17:20.152036	f	f	\N	f	f	f	f	f	UCZ5rBfggwiDJP99WygU62Wg.jpg	2025-04-02 00:00:00
\.


--
-- Data for Name: translation; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.translation (varname, en, de, es, fr, pt, nl, it, se) FROM stdin;
navtab1	video	video	vídeo	vidéo	vídeo	video	video	video
navtab2	channel	kanal	canal	canal	canal	kanaal	canale	kanal
navtab3	playlist	playlist	playlist	playlist	playlist	afspeellijst	playlist	spellista
navtab4	category	kategorie	categoría	catégorie	categoria	categorie	categoria	kategori
navtab5	settings	einstellungen	ajustes	paramètres	configurações	instellingen	impostazioni	inställningar
navtab6	user	benutzer	usuario	usager	usuário	gebruiker	utente	användare
navtab7	language	sprachen	idiomas	langues	idiomas	sprog	lingue	språk
\.


--
-- Data for Name: video; Type: TABLE DATA; Schema: public; Owner: altcen
--

COPY public.video (id) FROM stdin;
34
35
36
37
38
\.


--
-- Name: altcen_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.altcen_user_id_seq', 35, true);


--
-- Name: category_cat_id_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.category_cat_id_seq', 1, false);


--
-- Name: counter_hash_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.counter_hash_seq', 1, false);


--
-- Name: crypto_id_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.crypto_id_seq', 1, false);


--
-- Name: email_list_id_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.email_list_id_seq', 1, false);


--
-- Name: entity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.entity_id_seq', 38, true);


--
-- Name: language_lang_id_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.language_lang_id_seq', 1, false);


--
-- Name: playlist_id_seq; Type: SEQUENCE SET; Schema: public; Owner: altcen
--

SELECT pg_catalog.setval('public.playlist_id_seq', 16, true);


--
-- Name: entity entity_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.entity
    ADD CONSTRAINT entity_pkey PRIMARY KEY (id);


--
-- Name: mv_video; Type: MATERIALIZED VIEW; Schema: public; Owner: altcen
--

CREATE MATERIALIZED VIEW public.mv_video AS
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
    source.ytc_title,
    source.ytc_id,
    (setweight(to_tsvector((COALESCE(entity.extractor_data, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(entity.title, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(entity.description, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(entity.category, ''::character varying))::text), 'D'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_title, ''::character varying))::text), 'C'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_id, ''::character varying))::text), 'D'::"char") || setweight(to_tsvector((COALESCE(entity.tags, ''::character varying))::text), 'D'::"char"))))))) AS document
   FROM ((public.entity
     JOIN public.content ON ((content.video_id = entity.id)))
     JOIN public.source ON ((source.id = content.source_id)))
  WHERE ((entity.yt_deleted OR entity.yt_limited) AND (entity.exists_ia OR entity.exists_ac) AND entity.allow)
  GROUP BY entity.id, source.ytc_title, source.ytc_id
  ORDER BY entity.id DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_video OWNER TO altcen;

--
-- Name: mv_category; Type: MATERIALIZED VIEW; Schema: public; Owner: altcen
--

CREATE MATERIALIZED VIEW public.mv_category AS
 SELECT category.cat_id,
    category.cat_name,
    category.cat_image,
    count(mv_video.category) AS cat_count
   FROM (public.mv_video
     JOIN public.category ON (((category.cat_name)::text = (mv_video.category)::text)))
  GROUP BY category.cat_id, category.cat_name, category.cat_image
  ORDER BY (count(mv_video.category)) DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_category OWNER TO altcen;

--
-- Name: source source_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.source
    ADD CONSTRAINT source_pkey PRIMARY KEY (id);


--
-- Name: mv_channel; Type: MATERIALIZED VIEW; Schema: public; Owner: altcen
--

CREATE MATERIALIZED VIEW public.mv_channel AS
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
           FROM public.entity entity_1
          WHERE (source.id = entity_1.id)) AS allow,
    count(source.id) AS total,
    count(source.id) FILTER (WHERE ((entity.yt_deleted OR entity.yt_limited) AND (entity.exists_ia OR entity.exists_ac) AND entity.allow)) AS limited,
    count(source.id) FILTER (WHERE ((entity.exists_ia OR entity.exists_ac) AND entity.allow)) AS archived,
    (setweight(to_tsvector((COALESCE(source.ytc_id, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_title, ''::character varying))::text), 'A'::"char") || (setweight(to_tsvector((COALESCE(source.ytc_description, ''::character varying))::text), 'A'::"char") || setweight(to_tsvector((COALESCE(source.ytc_customurl, ''::character varying))::text), 'A'::"char")))) AS document
   FROM ((public.entity
     JOIN public.content ON ((content.video_id = entity.id)))
     JOIN public.source ON ((source.id = content.source_id)))
  GROUP BY source.id
 HAVING (count(source.id) > 0)
  ORDER BY source.id DESC
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_channel OWNER TO altcen;

--
-- Name: entity _entity_extractor_type; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.entity
    ADD CONSTRAINT _entity_extractor_type UNIQUE (extractor_key, extractor_data, type);


--
-- Name: altcen_user altcen_user_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.altcen_user
    ADD CONSTRAINT altcen_user_pkey PRIMARY KEY (id);


--
-- Name: category category_cat_name_key; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT category_cat_name_key UNIQUE (cat_name);


--
-- Name: category category_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT category_pkey PRIMARY KEY (cat_id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (id);


--
-- Name: counter counter_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.counter
    ADD CONSTRAINT counter_pkey PRIMARY KEY (hash);


--
-- Name: crypto crypto_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.crypto
    ADD CONSTRAINT crypto_pkey PRIMARY KEY (id);


--
-- Name: email_list email_list_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.email_list
    ADD CONSTRAINT email_list_pkey PRIMARY KEY (id);


--
-- Name: ia_upload_log ia_upload_log_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.ia_upload_log
    ADD CONSTRAINT ia_upload_log_pkey PRIMARY KEY (date, extractor_id);


--
-- Name: language language_lang_name_key; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.language
    ADD CONSTRAINT language_lang_name_key UNIQUE (lang_name);


--
-- Name: language language_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.language
    ADD CONSTRAINT language_pkey PRIMARY KEY (lang_id);


--
-- Name: playlist playlist_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.playlist
    ADD CONSTRAINT playlist_pkey PRIMARY KEY (id);


--
-- Name: translation translation_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.translation
    ADD CONSTRAINT translation_pkey PRIMARY KEY (varname);


--
-- Name: video video_pkey; Type: CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.video
    ADD CONSTRAINT video_pkey PRIMARY KEY (id);


--
-- Name: channel_document_gin_idx; Type: INDEX; Schema: public; Owner: altcen
--

CREATE INDEX channel_document_gin_idx ON public.mv_channel USING gin (document);


--
-- Name: mv_altcen_user_gin_idx; Type: INDEX; Schema: public; Owner: altcen
--

CREATE INDEX mv_altcen_user_gin_idx ON public.mv_altcen_user USING gin (document);


--
-- Name: mv_altcen_user_unique_idx; Type: INDEX; Schema: public; Owner: altcen
--

CREATE UNIQUE INDEX mv_altcen_user_unique_idx ON public.mv_altcen_user USING btree (id, username);


--
-- Name: mv_category_unique_idx; Type: INDEX; Schema: public; Owner: altcen
--

CREATE UNIQUE INDEX mv_category_unique_idx ON public.mv_category USING btree (cat_id, cat_name);


--
-- Name: mv_playlist_gin_idx; Type: INDEX; Schema: public; Owner: altcen
--

CREATE INDEX mv_playlist_gin_idx ON public.mv_playlist USING gin (document);


--
-- Name: mv_playlist_id_idx; Type: INDEX; Schema: public; Owner: altcen
--

CREATE UNIQUE INDEX mv_playlist_id_idx ON public.mv_playlist USING btree (id, hashid);


--
-- Name: video_document_gin_idx; Type: INDEX; Schema: public; Owner: altcen
--

CREATE INDEX video_document_gin_idx ON public.mv_video USING gin (document);


--
-- Name: content content_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.content
    ADD CONSTRAINT content_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.source(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: content content_video_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.content
    ADD CONSTRAINT content_video_id_fkey FOREIGN KEY (video_id) REFERENCES public.video(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: playlist playlist_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.playlist
    ADD CONSTRAINT playlist_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.altcen_user(id);


--
-- Name: source source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.source
    ADD CONSTRAINT source_id_fkey FOREIGN KEY (id) REFERENCES public.entity(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: video video_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altcen
--

ALTER TABLE ONLY public.video
    ADD CONSTRAINT video_id_fkey FOREIGN KEY (id) REFERENCES public.entity(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: mv_altcen_user; Type: MATERIALIZED VIEW DATA; Schema: public; Owner: altcen
--

REFRESH MATERIALIZED VIEW public.mv_altcen_user;


--
-- Name: mv_video; Type: MATERIALIZED VIEW DATA; Schema: public; Owner: altcen
--

REFRESH MATERIALIZED VIEW public.mv_video;


--
-- Name: mv_category; Type: MATERIALIZED VIEW DATA; Schema: public; Owner: altcen
--

REFRESH MATERIALIZED VIEW public.mv_category;


--
-- Name: mv_channel; Type: MATERIALIZED VIEW DATA; Schema: public; Owner: altcen
--

REFRESH MATERIALIZED VIEW public.mv_channel;


--
-- Name: mv_playlist; Type: MATERIALIZED VIEW DATA; Schema: public; Owner: altcen
--

REFRESH MATERIALIZED VIEW public.mv_playlist;


--
-- PostgreSQL database dump complete
--

