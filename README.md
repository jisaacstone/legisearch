These projects are built on top of the legistar api.

[legistar api notes](legistar.md)
  
[example of the data you can get from the api](documentation/sanjose.json)


## Under Progress

This repo is being reorganized.

The old use was a static site generation for meeting agenda searches.
This is currently broken.
I want to get it working again.
Currently I am rewriting and reorganizing the code to be more general purpose.
Legisearch has been split from a stand-alone script.
The useful bits are moved to `query.py`.
I have used those bits to build a new tool on top, that generates calendars.
That tool is [here](https://www.jisaacstone.com/legiscal/).

So. `query.py` is definitely working.
The rest is probably not.


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


# Old documentation below - mostly out of date


## Legisearch - legacy. TODO: cleanup

fetched city meeting data from legistar and generates a single-page static html file for rapid searching through agenda item titles

working example [here](http://www.jisaacstone.com/projects/councildoc.html)

The main script is `legisearch`

It requires python3.8 or greater to run.

`legisearch fetch -n NAMESPACE` will pull events from legistar and store in a sqlite db.

`legisearch generate -n NAMESPACE` will create NAMESPACE.html single-page webapp, with css, javascript and data embedded in a single file.

known namespaces

| namespace | city |
| --- | --- |
| mountainview | Mountain View, CA |
| sunnyvaleca | Sunnyvale, CA |
| santaclara | Santa Clara, CA |
| sanjose | San Jose, CA |
| bart | BART |

This was built for mountain view. Each city stores the data a bit differently.
More work needs to be done to make it portable across cities.

## Legiscal

This will be a web server that generates ical feeds from legistar meeting body info
