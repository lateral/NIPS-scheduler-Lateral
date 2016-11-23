#!/usr/bin/env python
"""
API calls:
----------
All respond with HTML.

/ GET
Respond with the list of events, unfiltered.

/search/keywords=deep+learning GET
Respond with the list of events matching the specified keywords.

/tag/Language GET
Respond with the list of events in the specified category ("tag").

/6216/ GET
Respond with information about the specified event (the ids are those from the
NIPS website), including a list of related talks and related arxiv papers.

/schedule/COOKIE_ID GET
Respond with a printable version of the schedule, the user being specified by
COOKIE_ID (so that the schedule can be shared).

/add/?event_id=6216 POST
Add the specifed event to the schedule of the user specified by the cookie
Responds as per /schedule/ (after making the requested change).
(response code is always 200).

/remove/?event_id=6216 POST
Remove the specifed event to the schedule of the user specified by the cookie
Responds as per /schedule/ (after making the requested change).
(response code is always 200, even if event not in the users schedule).

/related-arxiv-papers/6216/ GET
Respond with arXiv papers related to the event number 6216.

/static/FILENAME GET
Serve whatever static file is specified (i.e. CSS and javascript).

Templates:
----------
All page templates are stored in the folder `templates/`.
Pages that list all events and pages that detail any particular event have a
two column layout.  This layout is controlled by the template `main.html`,
which is extended by `events.html` and `event.html` respectively.
"""

import argparse
import tornado.ioloop
import tornado.web
import tornado.template
import ujson
import requests
import random
import logging

from requests import HTTPError
from lateral.api import API
from argparse import RawTextHelpFormatter

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

COOKIE_NAME = 'nipsscheduler'

CONTENT_TYPE = "Content-Type"
APP_JSON = "application/json"

NUM_RESULTS = 4
NUM_EVENTS = 50

ARXIV_ENDPOINT = 'http://arxiv-api.lateral.io'


class APIHandler(tornado.web.RequestHandler):

    def initialize(self, api, event_cache):
        self.api = api
        self.event_cache = event_cache

    def get_schedule_items(self, user_id):
        # get preferences for the user
        prefs = self.api.get_users_preferences(user_id)
        event_ids = [pref['document_id'] for pref in prefs]
        # get events from the cache
        events = [self.event_cache[event_id] for event_id in event_ids]
        # sort by start_time_numeric
        events = sorted(events,
                        key=lambda event: event['meta']['start_time_numeric'])
        return events


class RelatedArxivPapersHandler(APIHandler):

    def get(self, event_id):
        """
        Respond with the related arXiv papers (as HTML).
        """
        text = self.event_cache[event_id]['text']
        url = ARXIV_ENDPOINT + '/recommend-by-text/'
        payload = ujson.dumps(dict(text=text))
        headers = {'subscription-key': self.api.key, CONTENT_TYPE: APP_JSON}
        response = requests.request("POST", url, data=payload, headers=headers)
        results = ujson.loads(response.text)[:NUM_RESULTS]
        self.render('arxiv_results.html', papers=results)


class UserHandler(APIHandler):

    def prepare(self):
        self.user_id = self.get_cookie(COOKIE_NAME)
        if not self.user_id:  # never seen user before
            # create a new user in the API
            user = self.api.post_user()
            self.user_id = user['id']
            # set the cookie to be their user id
            self.set_cookie(COOKIE_NAME, self.user_id)


class EventsHandler(UserHandler):

    def respond_with(self, title, events):
        # get the user's schedule
        schedule_items = self.get_schedule_items(self.user_id)
        self.render('events.html',
                    events_title=title,
                    events=events,
                    schedule_items=schedule_items,
                    user_id=self.user_id)

    def get(self):
        events = random.sample(self.event_cache.values(), NUM_EVENTS)
        self.respond_with('All events', events)


class TagHandler(EventsHandler):

    def get(self, tag):
        matches = self.api.get_tags_documents(tag, fields='', per_page=NUM_EVENTS)
        events = [self.event_cache[match['id']] for match in matches]
        title = 'Tag: ' + tag.replace('_', ' ')
        self.respond_with(title, events)


class SearchHandler(EventsHandler):

    def get(self):
        keywords = self.get_argument('keywords', '')
        matches = self.api.get_documents(keywords=keywords, fields='',
                                         per_page=NUM_EVENTS)
        events = [self.event_cache[match['id']] for match in matches]
        title = 'Search: ' + keywords
        self.respond_with(title, events)


class EventHandler(UserHandler):

    def get_related_events(self, event_id):
        matches = self.api.get_documents_similar(
            event_id, fields='', exclude='[%s]' % event_id,
            number=NUM_RESULTS)
        events = [self.event_cache[match['id']] for match in matches]
        return events

    def get(self, event_id):
        event = self.api.get_document(event_id)
        # get the user's schedule
        schedule_items = self.get_schedule_items(self.user_id)
        self.render('event.html',
                    user_id=self.user_id,
                    tags=self.api.get_documents_tags(event_id),
                    schedule_items=schedule_items,
                    related_events=self.get_related_events(event_id),
                    **event)

    def respond_with_schedule(self):
        # get the user's schedule
        schedule_items = self.get_schedule_items(self.user_id)
        self.render('schedule.html',
                    items=schedule_items,
                    user_id=self.user_id)


class AddToScheduleHandler(EventHandler):

    def post(self):
        event_id = self.get_argument('event_id')
        try:
            self.api.post_users_preference(self.user_id, event_id)
        except HTTPError as e:
            print e.request.url
            if e.response.status_code != 409:  # already added
                raise e
        self.respond_with_schedule()


class RemoveFromScheduleHandler(EventHandler):

    def post(self):
        event_id = self.get_argument('event_id')
        try:
            # handle 404 for unknown document quietly
            self.api.delete_users_preference(self.user_id, event_id)
        except HTTPError as e:
            if e.response.status_code != 404:
                raise e
        self.respond_with_schedule()


class PrintableScheduleHandler(APIHandler):

    def initialize(self, api, event_cache):
        self.api = api
        self.event_cache = event_cache

    def get(self, user_id):
        schedule_items = self.get_schedule_items(user_id)
        self.render('printable_schedule.html', user_id=user_id,
                    items=schedule_items)


def build_event_cache(api):
    """
    Fetch all events (documents) from the API and return them as a dictionary
    mapping id -> response.
    """
    events = {}
    page = 1
    while True:
        results = api.get_documents(page=page, per_page=100)
        if results == []:
            break
        for result in results:
            events[result['id']] = result
        page += 1
    return events


def build_application(key):
    api = API(key)
    event_cache = build_event_cache(api)
    resources = {'api': api, 'event_cache': event_cache}
    handlers = [
        (r"/{0,1}", EventsHandler, resources),
        (r"/search/{0,1}", SearchHandler, resources),
        (r"/tag/(.*)/{0,1}", TagHandler, resources),
        (r"/([0-9]+)/{0,1}", EventHandler, resources),
        (r"/add/{0,1}", AddToScheduleHandler, resources),
        (r"/remove/{0,1}", RemoveFromScheduleHandler, resources),
        (r"/related-arxiv-papers/([0-9]+)/{0,1}", RelatedArxivPapersHandler, resources),
        (r"/schedule/([A-Za-z-_0-9]+)/{0,1}", PrintableScheduleHandler, resources),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': 'static/'}),
    ]

    # FIXME remove debug=True when in production
    application = tornado.web.Application(handlers,
                                          template_path='templates/',
                                          debug=True)
    return application

HELP_STR = """
Start the NIPS Scheduler API.
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=HELP_STR,
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--port',
                        help='port to run API on',
                        type=int,
                        required=True)
    parser.add_argument('--key',
                        help='read/write key for the Lateral API',
                        required=True)
    args = parser.parse_args()
    application = build_application(args.key)
    application.listen(args.port)
    tornado.ioloop.IOLoop.instance().start()
