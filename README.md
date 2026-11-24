These projects are built on top of the Legistar api.

[legistar api notes](documentation/legistar.md)
  
[example of the data you can get from the api](documentation/sanjose.json)

[build and run the web site locally](documentation/website.md)

## TLDR

**Legisearch** is a lightweight CLI tool built on top of the Legistar API. 

**Legistar** is a civictech product line by Granicus with the goal of digitizing city council minutes, voting records, and agendas. Want to know what your local politics is covering? Legistar lets you peek into the topics discussed and how the [local] elected people on your ballot vote. 

The actual contents can be manually downloaded at [city].legistar.com, ie the public web frontend hosting PDF’s and HTML tables. This is an unwieldy task, and so the goal of this tool is to provide the means to download fetched city meeting data into a local database (this avoids constantly pinging the API), and make it searchable.

Legisearch bypasses manual web downloads by downloading it into a local SQLite database, and allowing you to search that way. 

## Structure

Because the Legistar API isn't built for high-speed querying, live real-time search is highly impractical. This repo solves that issue by having local data caching instead.

The stuff we are interested in (what items were talked about in a particular meeting, how people voted, etc) is not queryable from the api.

That information is all behind `event` or `matter` ids.

So to achieve search it is necessary to pull all data from legistar first, and store it ourselves.
I am currently using sqlite. It is I think good enough for this purpose.
Fetching the data and storing it is the easy part. Search is still undecided.
I had a very basic search functionality working earlier.
But it has significant limitations.
Would be great to find some kind of library or out-of-the-box solution.


## Legisearch

fetched city meeting data from legistar and sort in a searchable db.

The main script is `legisearch`

It requires python3.8 or greater to run.

`legisearch reset -n NAMESPACE` will create a new db with empty tables, wiping any preexisting data for that namespace.

`legisearch fetch -n NAMESPACE` will pull events from legistar and store in a sqlite db.

`legisearch search -n NAMESPACE STRING` will search all previously fetched events for STRING.

## Examples

`legisearch reset -n sanjose`

`legisearch fetch -n sanjose`

—> Switch from San Jose to Mountain View
`legisearch reset -n mountainview`

`legisearch search -n sanjose -q "housing"`

`pwd`

`... /python-workspace/legisearch`

`python legisearch/peek.py
=== ALL UNFILTERED ITEMS (5 found) ===
Date: 2017-09-12 13:30:00.000000 | Body: City Council | Agenda #: 
Title: Closed Session Agenda
full_text_lower content: None... `


## Legiscal

Generates ical feeds from legistar meeting body info.
There is a flask app in development. But the code works as a library.
There is a functional project using the code [here](https://www.jisaacstone.com/legiscal/index.html)


## Namespaces

Known namespaces in Santa Clara County:

| namespace | city |
| --- | --- |
| mountainview | Mountain View, CA |
| sunnyvaleca | Sunnyvale, CA |
| santaclara | Santa Clara, CA |
| sanjose | San Jose, CA |
| bart | BART |

Many more exist, check the [subdomain crawler results](documentation/legistar) to see if your local legislative body is in.
