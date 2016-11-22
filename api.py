#!/usr/bin/env python
import argparse
import tornado.ioloop
import tornado.web
import tornado.template
import ujson
import requests
import random

from requests import HTTPError
from lateral.api import API
from argparse import RawTextHelpFormatter

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
        events = sorted(events, key=lambda event: event['meta']['start_time_numeric'])
        return events


class RelatedArxivPapersHandler(APIHandler):

    def get(self, event_id):
        """
        Respond with the related arXiv papers (as HTML).
        """
        text = self.event_cache[event_id]['text']
        url = ARXIV_ENDPOINT + '/recommend-by-text/'
        payload = ujson.dumps(dict(text=text))
        headers = { 'subscription-key': self.api.key, CONTENT_TYPE: APP_JSON }
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
        self.respond_with('Events', events)


class TagHandler(EventsHandler):

    def get(self, tag):
        matches = self.api.get_tags_documents(tag, fields='', per_page=NUM_EVENTS)
        events = [self.event_cache[match['id']] for match in matches]
        title = 'Tag: ' + tag.replace('_', ' ')
        self.respond_with(title, events)


class SearchHandler(EventsHandler):

    def get(self):
        keywords = self.get_argument('keywords', '')
        matches = self.api.get_documents(keywords=keywords, fields='', per_page=NUM_EVENTS)
        events = [self.event_cache[match['id']] for match in matches]
        title = 'Keywords: ' + keywords
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
            # handle the 500 response that is raised when already exists (this needs to be fixed in Lateral API)
            self.api.post_users_preference(self.user_id, event_id)
        except HTTPError as e:
            print e.request.url
            if e.response.status_code != 409:
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
        self.render('printable_schedule.html', user_id=user_id, items=schedule_items)


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
    application = tornado.web.Application([
        (r"/{0,1}", EventsHandler, resources),
        (r"/search/{0,1}", SearchHandler, resources),
        (r"/tag/(.*)/{0,1}", TagHandler, resources),
        (r"/([0-9]+)/{0,1}", EventHandler, resources),
        (r"/add/{0,1}", AddToScheduleHandler, resources),
        (r"/remove/{0,1}", RemoveFromScheduleHandler, resources),
        (r"/related-arxiv-papers/([0-9]+)/{0,1}", RelatedArxivPapersHandler, resources),
        (r"/schedule/([A-Za-z-_0-9]+)/{0,1}", PrintableScheduleHandler, resources),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': 'static/'}),
    ], template_path='templates/', debug=True) # FIXME remove debug=True for deployment
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
