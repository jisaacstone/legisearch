#!/usr/bin/env bash
set -e
if [ -z "$1" ]; then
  echo "usage: ${0} NAMESPACE"
  exit 1
fi

dbname="${1}.db"

if [ ! -f "${dbname}" ]; then
  echo "${dbname}" not found
  exit 1
fi

sqlite3 $1.db '.mode json' ".once static_web/${1}.events.json" 'select * from events;'
sqlite3 $1.db '.mode json' ".once static_web/${1}.items.json" 'select * from items;'
sqlite3 $1.db '.mode json' ".once static_web/${1}.bodies.json" 'select * from bodies;'
