#!/usr/bin/env bash

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER adcm with encrypted password '$POSTGRES_ADCM_PASS';
	CREATE DATABASE adcm;
	GRANT ALL ON DATABASE adcm TO adcm;
	ALTER DATABASE adcm OWNER TO adcm;
EOSQL
