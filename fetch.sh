#!/usr/bin/env bash
set -ex
mkdir calendars
for year in 2013 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023; do
  curl 'https://mountainview.legistar.com/Calendar.aspx' \
    -o calendars/${year}-city-council.html \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -H 'Origin: https://mountainview.legistar.com' \
    -H 'Cookie: Setting-344-Calendar Options=info|; Setting-344-Calendar Year='${year}'; Setting-344-Calendar Body=22578'
done
