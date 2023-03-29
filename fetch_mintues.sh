#!/usr/bin/env bash
set -ex

for fn in $(ls calendars); do
  short_fn="${fn%.html}"
  mkdir -p "minutes/${short_fn}"
  for link in $(./extract_links.py "calendars/${fn}"); do
    identifier="${link#*\?}"
    outfile="minutes/${short_fn}/${identifier}.pdf"
    if [ -f "${outfile}" ]; then
      echo skipping "${outfile}" - already downloaded
    else
      curl "${link}" -o "minutes/${short_fn}/${identifier}.pdf"
    fi
  done
done
