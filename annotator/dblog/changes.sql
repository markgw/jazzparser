/*
 * Database schema change log for the annotated chord database
 *
 * SQLite database.
 * For the initial schema which these changes modify, see initial.sql.
 * For the complete latest schema, run (from ..)
 *  ./django-admin sqlall sequences
 *
 */
 
/* Rev 935 */
CREATE TABLE "sequences_song" (
    "id" integer NOT NULL PRIMARY KEY,
    "name" varchar(50) NOT NULL,
    "key" varchar(20),
    "notes" text
)
;
ALTER TABLE "sequences_chordsequence" 
	ADD COLUMN "song_id" integer REFERENCES "sequences_song" ("id");
ALTER TABLE "sequences_chordsequence"
	ADD COLUMN "description" text;
CREATE INDEX "sequences_chordsequence_song_id" ON "sequences_chordsequence" ("song_id");


/* Rev 936 */
/* Remove "name" and "key" columns from "sequences_chordsequence" */
BEGIN TRANSACTION;
CREATE TEMPORARY TABLE seq_backup (
    "id" integer NOT NULL PRIMARY KEY,
    "song_id" integer NOT NULL REFERENCES "sequences_song" ("id"),
    "description" text,
    "bar_length" integer NOT NULL,
    "first_chord_id" integer REFERENCES "sequences_chord" ("id"),
    "notes" text,
    "analysis_omitted" bool NOT NULL,
    "omissions" text,
    "source_id" integer REFERENCES "sequences_source" ("id")
);
INSERT INTO seq_backup 
	SELECT id,song_id,description,bar_length,first_chord_id,
		notes,analysis_omitted,omissions,source_id 
	FROM "sequences_chordsequence";
DROP TABLE sequences_chordsequence;
CREATE TABLE "sequences_chordsequence" (
    "id" integer NOT NULL PRIMARY KEY,
    "song_id" integer NOT NULL REFERENCES "sequences_song" ("id"),
    "description" text,
    "bar_length" integer NOT NULL,
    "first_chord_id" integer REFERENCES "sequences_chord" ("id"),
    "notes" text,
    "analysis_omitted" bool NOT NULL,
    "omissions" text,
    "source_id" integer REFERENCES "sequences_source" ("id")
)
;
INSERT INTO sequences_chordsequence SELECT * FROM seq_backup;
DROP TABLE seq_backup;
COMMIT;

/* Rev 941 */
/* Change type of "description" on "sequences_chordsequence" */
/* Sql from SQLite Browser */
CREATE TEMPORARY TABLE TEMP_TABLE(id integer PRIMARY KEY, song_id integer, description varchar(256), bar_length integer, first_chord_id integer, notes text, analysis_omitted bool, omissions text, source_id integer);
INSERT INTO TEMP_TABLE SELECT id, song_id, description, bar_length, first_chord_id, notes, analysis_omitted, omissions, source_id FROM sequences_chordsequence;
DROP TABLE sequences_chordsequence;
CREATE TABLE sequences_chordsequence (id integer PRIMARY KEY, song_id integer, description varchar(256), bar_length integer, first_chord_id integer, notes text, analysis_omitted bool, omissions text, source_id integer);
INSERT INTO sequences_chordsequence SELECT id, song_id, description, bar_length, first_chord_id, notes, analysis_omitted, omissions, source_id FROM TEMP_TABLE;
DROP TABLE TEMP_TABLE;

/* Rev 951 */
/* Adding the new midi data table */
CREATE TABLE "sequences_mididata" (
    "id" integer NOT NULL PRIMARY KEY,
    "midi_file" varchar(100) NOT NULL,
    "sequence_id" integer NOT NULL REFERENCES "sequences_chordsequence" ("id")
);
CREATE INDEX "sequences_mididata_sequence_id" ON "sequences_mididata" ("sequence_id");

/* Rev 952 */
/* Adding new table to align chord sequences with midi files */
CREATE TABLE "sequences_midichordalignment" (
    "id" integer NOT NULL PRIMARY KEY,
    "midi_id" integer NOT NULL REFERENCES "sequences_mididata" ("id"),
    "chord_id" integer NOT NULL REFERENCES "sequences_chord" ("id"),
    "start" integer NOT NULL,
    "end" integer NOT NULL
)
;
CREATE INDEX "sequences_midichordalignment_midi_id" ON "sequences_midichordalignment" ("midi_id");
CREATE INDEX "sequences_midichordalignment_chord_id" ON "sequences_midichordalignment" ("chord_id");


/* Rev 975 */
/* Adding new field "name" to midi data table */

/* Rev 936 */
/* Remove "name" and "key" columns from "sequences_chordsequence" */
BEGIN TRANSACTION;
CREATE TEMPORARY TABLE temp (
    "id" integer NOT NULL PRIMARY KEY,
    "midi_file" varchar(100) NOT NULL,
    "sequence_id" integer NOT NULL REFERENCES "sequences_chordsequence" ("id"),
    "name" varchar(200) NOT NULL
);
INSERT INTO temp 
	SELECT id,midi_file,sequence_id,""
	FROM "sequences_mididata";
DROP TABLE "sequences_mididata";
CREATE TABLE "sequences_mididata" (
    "id" integer NOT NULL PRIMARY KEY,
    "midi_file" varchar(100) NOT NULL,
    "sequence_id" integer NOT NULL REFERENCES "sequences_chordsequence" ("id"),
    "name" varchar(200) NOT NULL
)
;
INSERT INTO sequences_mididata SELECT * FROM temp;
DROP TABLE temp;
COMMIT;

/** Adding "alternative" column to the ChordSequence model **/
ALTER TABLE sequences_chordsequence ADD COLUMN "alternative" bool NOT NULL DEFAULT 0;
