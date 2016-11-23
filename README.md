# NIPS-scheduler-Lateral

A web service for building a personalised schedule for NIPS 2016, using the Lateral API for finding similar talks and posters.  Written in Python 2.7.  Released as an example usage of the Lateral API.

Data was scraped from the NIPS website and pushed into the Lateral API.  Events (i.e. talks, posters, workshops and so on) were represented as documents and categories were represented as tags.  When a user visits the website for the first time, a cookie is set, and the value for that cookie is used to represent the user inside the Lateral API.  Each time a user adds an event to their schedule, a preference is created in the Lateral API to represent this.

## Required packages

 - `apiwrappy` : a Python client library for the Lateral API (FIXME release, add link).
 - `requests` : for making API requests directly.
 - `tornado` : the web server.

## Usage:

In order to run this, you'd need the subscription key with read/write priviledges to the NIPS 2016 dataset at Lateral.  To start the API, run:

```
python api.py --port 1024 --key <KEY>
```
