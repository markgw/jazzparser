/*
 * State of SQLite database at rev 934.
 * For subsequent progressive changes, see changes.sql
 */
BEGIN;
CREATE TABLE "sequences_chordtype" (
    "id" integer NOT NULL PRIMARY KEY,
    "symbol" varchar(10),
    "order" integer NOT NULL
)
;
CREATE TABLE "sequences_source" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(30) NOT NULL
)
;
CREATE TABLE "sequences_chord" (
    "id" integer NOT NULL PRIMARY KEY,
    "root" integer NOT NULL,
    "type_id" integer NOT NULL REFERENCES "sequences_chordtype" ("id"),
    "additions" varchar(15),
    "bass" integer,
    "next_id" integer,
    "duration" integer NOT NULL,
    "category" varchar(20),
    "sequence_id" integer
)
;
CREATE TABLE "sequences_chordsequence" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(50) NOT NULL,
    "key" varchar(20),
    "bar_length" integer NOT NULL,
    "first_chord_id" integer REFERENCES "sequences_chord" ("id"),
    "notes" text,
    "analysis_omitted" bool NOT NULL,
    "omissions" text,
    "source_id" integer REFERENCES "sequences_source" ("id")
)
;
CREATE TABLE "sequences_treeinfo" (
    "id" integer NOT NULL PRIMARY KEY,
    "chord_id" integer NOT NULL UNIQUE REFERENCES "sequences_chord" ("id"),
    "coord_unresolved" bool NOT NULL,
    "coord_resolved" bool NOT NULL
)
;
CREATE TABLE "sequences_skippedsequence" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(20) NOT NULL,
    "reason" text
)
;
CREATE INDEX "sequences_chord_type_id" ON "sequences_chord" ("type_id");
CREATE INDEX "sequences_chord_next_id" ON "sequences_chord" ("next_id");
CREATE INDEX "sequences_chord_sequence_id" ON "sequences_chord" ("sequence_id");
CREATE INDEX "sequences_chordsequence_first_chord_id" ON "sequences_chordsequence" ("first_chord_id");                                                                                          
CREATE INDEX "sequences_chordsequence_source_id" ON "sequences_chordsequence" ("source_id");
COMMIT;
