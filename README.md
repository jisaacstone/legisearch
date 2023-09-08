These projects are built on top of the legistar api.

[legistar api notes](legistar.md)
  
[exampl of the data you can get from the api](documentation/sanjose.json)

## Legisearch

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

This was built for mountain view. Each city stores the data a bit differently.
More work needs to be done to make it portable across cities.

## Legiscal

This will be a web server that generates ical feeds from legistar meeting body info
