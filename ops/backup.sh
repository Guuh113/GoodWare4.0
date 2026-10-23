#!/bin/sh
set -eu
umask 077
while true; do
    target="/backups/goodware-$(date -u +%Y%m%dT%H%M%SZ).dump"
    if pg_dump -Fc -f "$target.tmp"; then
        mv "$target.tmp" "$target"
        find /backups -type f -name 'goodware-*.dump' -mtime +7 -delete
        echo 'Backup PostgreSQL concluído.'
    else
        rm -f "$target.tmp"
        echo 'Falha no backup PostgreSQL.' >&2
    fi
    sleep 86400
done
