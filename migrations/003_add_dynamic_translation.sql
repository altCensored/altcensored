/*
 Navicat Premium Data Transfer

 Source Server         : altcensored.org
 Source Server Type    : PostgreSQL
 Source Server Version : 120004
 Source Host           : altcensored.org:5432
 Source Catalog        : altcen
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 120004
 File Encoding         : 65001

 Date: 05/09/2020 01:15:08
*/


-- ----------------------------
-- Table structure for translation
-- ----------------------------
DROP TABLE IF EXISTS "public"."translation";
CREATE TABLE "public"."translation" (
  "varname" text COLLATE "pg_catalog"."default" NOT NULL,
  "en" text COLLATE "pg_catalog"."default" NOT NULL,
  "de" text COLLATE "pg_catalog"."default",
  "es" text COLLATE "pg_catalog"."default",
  "fr" text COLLATE "pg_catalog"."default",
  "pt" text COLLATE "pg_catalog"."default",
  "nl" text COLLATE "pg_catalog"."default",
  "it" text COLLATE "pg_catalog"."default",
  "se" text COLLATE "pg_catalog"."default"
)
;

-- ----------------------------
-- Records of translation
-- ----------------------------
INSERT INTO "public"."translation" VALUES ('navtab1', 'video', 'video', 'vídeo', 'vidéo', 'vídeo', 'video', 'video', 'video');
INSERT INTO "public"."translation" VALUES ('navtab2', 'channel', 'kanal', 'canal', 'canal', 'canal', 'kanaal', 'canale', 'kanal');
INSERT INTO "public"."translation" VALUES ('navtab3', 'category', 'kategorie', 'categoría', 'catégorie', 'categoria', 'categorie', 'categoria', 'kategori');
INSERT INTO "public"."translation" VALUES ('navtab5', 'history', 'geschichte', 'historia', 'histoire', 'história', 'geschiedenis', 'storia', 'historia');
INSERT INTO "public"."translation" VALUES ('navtab6', 'settings', 'einstellungen', 'ajustes', 'paramètres', 'configurações', 'instellingen', 'impostazioni', 'inställningar');
INSERT INTO "public"."translation" VALUES ('navtab4', 'playlist', 'playlist', 'playlist', 'playlist', 'playlist', 'afspeellijst', 'playlist', 'spellista');
INSERT INTO "public"."translation" VALUES ('navtab7', 'user', 'benutzer', 'usuario', 'usager', 'usuário', 'gebruiker', 'utente', 'användare');
-- ----------------------------
-- Primary Key structure for table translation
-- ----------------------------
ALTER TABLE "public"."translation" ADD CONSTRAINT "varname_key" PRIMARY KEY ("varname");
