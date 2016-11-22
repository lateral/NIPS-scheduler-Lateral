#!/usr/bin/env python
import argparse
import tornado.ioloop
import tornado.web
import tornado.template
import logging
import ujson
import requests

from requests import HTTPError
from lateral.api import Api
from argparse import RawTextHelpFormatter

LOGGER = logging.getLogger('NIPS api')
COOKIE_NAME = 'nipsscheduler'

CONTENT_TYPE = "Content-Type"
APP_JSON = "application/json"

NUM_RESULTS = 4

ARXIV_ENDPOINT = 'http://arxiv-api.lateral.io'


class APIHandler(tornado.web.RequestHandler):

    def initialize(self, api):
        self.api = api

    def get_schedule_cards(self, user_id):
        # get preferences for the user
        prefs = self.api.get_users_preferences(user_id)
        event_ids = [pref['document_id'] for pref in prefs]
        # get all the documents, one by one
        cards = [self.api.get_document(event_id) for event_id in event_ids]
        # TODO sort by start_time_numeric
        return cards

    def get_related_papers(self, text):
        """
        Return the related arXiv papers according to the Lateral API as a
        Python list in the formated described here
        https://lateral.io/docs/arxiv-recommender/reference#arxiv-recommend-by-text-post
        """
        url = ARXIV_ENDPOINT + '/recommend-by-text/'
        payload = ujson.dumps(dict(text=text))
        headers = { 'subscription-key': self.api.key, CONTENT_TYPE: APP_JSON }
        response = requests.request("POST", url, data=payload, headers=headers)
        results = ujson.loads(response.text)
        return results[:NUM_RESULTS]


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

    def get(self):
        # get all the events
        keywords = self.get_argument('keywords', None)
        event_cards = self.api.get_documents(keywords=keywords)
        # get the user's schedule
        schedule_cards = self.get_schedule_cards(self.user_id)
        self.render('events.html',
                    event_cards=event_cards,
                    schedule_cards=schedule_cards,
                    user_id=self.user_id)


class EventHandler(UserHandler):

    def get(self, event_id):
        event = self.api.get_document(event_id)
        tags = self.api.get_documents_tags(event_id)
        # fetch the similar talks
        related_events = self.api.get_documents_similar(
            event_id, fields='meta,text', exclude='[%s]' % event_id,
            number=NUM_RESULTS)
        # fetch the similar arxiv papers, include them
        related_papers = self.get_related_papers(event['meta']['abstract_text'])
        # get the user's schedule
        schedule_cards = self.get_schedule_cards(self.user_id)
        self.render('event.html',
                    user_id=self.user_id,
                    tags=tags,
                    schedule_cards=schedule_cards,
                    related_events=related_events,
                    related_papers=related_papers, **event)

    def respond_with_schedule(self):
        # get the user's schedule
        schedule_cards = self.get_schedule_cards(self.user_id)
        self.render('schedule.html',
                    cards=schedule_cards,
                    user_id=self.user_id)


class AddToScheduleHandler(EventHandler):

    def post(self):
        event_id = self.get_argument('event_id')
        try:
            # handle the 500 response that is raised when already exists (this needs to be fixed in Lateral API)
            self.api.post_users_preference(self.user_id, event_id)
        except HTTPError as e:
            if e.response.status_code != 500:
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

    def initialize(self, api):
        self.api = api

    def get(self, user_id):
        schedule_cards = self.get_schedule_cards(user_id)
        self.render('printable_schedule.html', user_id=user_id,
                    schedule_cards=schedule_cards)


def build_application(key):
    resources = {'api': Api(key)}
    application = tornado.web.Application([
        (r"/{0,1}", EventsHandler, resources),
        (r"/([0-9]+)/{0,1}", EventHandler, resources),
        (r"/add/{0,1}", AddToScheduleHandler, resources),
        (r"/remove/{0,1}", RemoveFromScheduleHandler, resources),
        (r"/schedule/([A-Za-z-_0-9]+)/{0,1}", PrintableScheduleHandler, resources),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': 'static/'}),
    ], template_path='templates/', debug=True) # FIXME remove debug=True for deployment
    return application

HELP_STR = """
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
