FROM postgres:16-alpine

# SQL files in this folder are executed automatically when the database volume
# is first created.
COPY init.sql /docker-entrypoint-initdb.d/001-init.sql
