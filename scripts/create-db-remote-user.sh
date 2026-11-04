#!/usr/bin/env bash
# Creates, or rotates the password of, the PostgreSQL login used from outside the cluster (Adminer at
# https://jithendar.com/db/ and psql to db.jithendar.com:443). It is not the app's login: it can read and write
# table data (pg_read_all_data, pg_write_all_data) but cannot create, alter or drop objects or roles, and has at
# most 5 connections. Run from the repository root on a machine with kubectl access to mk4:
#
#   bash scripts/create-db-remote-user.sh          # create or rotate, prints the password once
#
# The password is also kept in Secret jithendar/jithendar-db-remote (keys username, password), never in Git.
# To remove access: kubectl delete -k k8s/db-access, then  DROP ROLE jithendar_remote;  as the jithendar user.
set -euo pipefail
CONTEXT=${KUBE_CONTEXT:-mk4}
ROLE=${ROLE:-jithendar_remote}
[[ $ROLE =~ ^[a-z_][a-z0-9_]{0,62}$ ]] || { echo "Invalid ROLE." >&2; exit 1; }
k() { kubectl --context "$CONTEXT" -n jithendar "$@"; }

PASSWORD=$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 32)
[[ ${#PASSWORD} -eq 32 ]] || { echo "Could not generate a password." >&2; exit 1; }

# The password goes in on stdin (not in a command line, where ps could show it). The jithendar user is the
# database owner and superuser of this instance; local socket connections inside the pod need no password.
k exec -i jithendar-postgres-0 -c postgres -- psql -X -q -v ON_ERROR_STOP=1 -U jithendar -d jithendar <<SQL
SET client_min_messages = warning;
\set role '$ROLE'
\set pass '$PASSWORD'
SELECT format('CREATE ROLE %I LOGIN', :'role') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 5 PASSWORD %L', :'role', :'pass') \gexec
SELECT format('GRANT CONNECT ON DATABASE jithendar TO %I', :'role') \gexec
SELECT format('GRANT pg_read_all_data, pg_write_all_data TO %I', :'role') \gexec
SQL

k create secret generic jithendar-db-remote --from-literal=username="$ROLE" --from-literal=password="$PASSWORD" \
  --dry-run=client -o yaml | k apply -f - >/dev/null

cat <<OUT
Login ready: user $ROLE, database jithendar.
Password (shown once; also in Secret jithendar/jithendar-db-remote):
  $PASSWORD
Adminer:  https://jithendar.com/db/  (System PostgreSQL, Server jithendar-postgres)
psql:     psql "host=db.jithendar.com port=443 dbname=jithendar user=$ROLE sslmode=verify-full sslrootcert=system"
OUT
