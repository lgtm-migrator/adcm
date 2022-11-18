#!/usr/bin/env bash

# sqlite3 binary must present in OS; path to sqlite DB file should be passed as script parameter

mkdir -p sql_tables

TABLES=$(
    sqlite3 "$1" "SELECT tbl_name FROM sqlite_master
    WHERE type='table'
    and tbl_name not like 'sqlite_%'
    and tbl_name != 'django_migrations';")

for TABLE in $TABLES; do

sqlite3 "$1" <<!
.headers off
.mode csv
.output "sql_tables/$TABLE.csv"
select * from $TABLE;
!

done
