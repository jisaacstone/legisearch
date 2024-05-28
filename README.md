These projects are built on top of the legistar api.

[legistar api notes](documentation/legistar.md)
  
[example of the data you can get from the api](documentation/sanjose.json)

[build and run the web site locally](documentation/website.md)


## Structure

The shape of the legistar api is such that real-time search is impractical.
The stuff we are interested in (what items were talked about in a particular meeting, how people voted, etc)
  is not queryable from the api.
That information is all behind `event` or `matter` ids.
So to achieve search it is necessary to pull all data from legistar first, and store it ourselves.
I am currently using sqlite. It is I think good enough for this purpose.
Fetching the data and storing it is the easy part. Search is still undecided.
I had a very basic search functionality working earlier.
But it has significant limitations.
Would be great to find some kind of library or out-of-the-box solution.


## Legisearch

fetched city meeting data from legistar and sore in a searchable db.

The main script is `legisearch`

It requires python3.8 or greater to run.

`legisearch reset -n NAMESPACE` will create a new db with empty tables, wiping any preexisting data for that namespace.

`legisearch fetch -n NAMESPACE` will pull events from legistar and store in a sqlite db.

`legisearch search -n NAMESPACE STRING` will search all previously fetched events for STRING.


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
