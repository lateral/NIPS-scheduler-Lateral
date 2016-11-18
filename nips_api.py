#!/usr/bin/env python
import argparse
import tornado.ioloop
import tornado.web
import tornado.template
import logging
import ujson

from requests import HTTPError
from lateral.api import Api
from argparse import RawTextHelpFormatter

LOGGER = logging.getLogger('NIPS api')
COOKIE_NAME = 'nipsscheduler'

CONTENT_TYPE = "Content-Type"
APP_JSON = "application/json"

#FIXME be consistent: documents or events?


class APIHandler(tornado.web.RequestHandler):

    def initialize(self, api):
        self.api = api

    def get_card(self, event_id):
        response = self.api.get_document(event_id)
        document = ujson.loads(response.text)
        # prepare LIP document object for use in tornado template
        meta = document['meta']
        authors = meta['authors'].split(', ')
        author_ids = meta['author_ids'].split(', ')
        return dict(id=document['id'], meta=meta, authors=authors, author_ids=author_ids)


class UserHandler(APIHandler):

    def prepare(self):
        self.user_id = self.get_cookie(COOKIE_NAME)
        if not self.user_id:  # never seen user before
            # create a new user in the API
            response = self.api.post_user()
            user = ujson.loads(response.text)
            self.user_id = user['id']
            # set the cookie to be their user id
            self.set_cookie(COOKIE_NAME, self.user_id)  # FIXME check expiry in browser


class RootHandler(UserHandler):

    def get(self):
        # TODO should be returning all the talks
        self.write(self.user_id)


class EventHandler(UserHandler):

    def get(self, event_id):
        #TODO fetch the similar talks, include them
        #TODO fetch the similar arxiv papers, include them
        card = self.get_card(event_id)
        self.render('event.html', related_cards=[], **card)

    def _respond_schedule(self):
        """
        respond with list of event ids preferenced, JSON encoded
        """
        request = self.api.get_users_preferences(self.user_id)
        prefs = ujson.loads(request.text)
        self.set_header(CONTENT_TYPE, APP_JSON)
        self.write(ujson.dumps(prefs))

    def post(self, event_id):
        # FIXME handle the 500 that is raised when already exists
        self.api.post_users_preference(self.user_id, event_id)
        self._respond_schedule()

    def delete(self, event_id):
        # FIXME handle 404
        self.api.delete_users_preference(self.user_id, event_id)
        self._respond_schedule()


class ScheduleHandler(APIHandler):

    def initialize(self, api):
        self.api = api

    def get(self, user_id):
        # get preferences for the user
        print user_id
        request = self.api.get_users_preferences(user_id)
        prefs = ujson.loads(request.text)
        event_ids = [pref['document_id'] for pref in prefs]
        # get all the documents, one by one
        cards = [self.get_card(event_id) for event_id in event_ids]
        # TODO sort by start_time_numeric
        self.render('schedule.html', id=user_id, cards=cards)


def build_application(key):
    resources = {'api': Api(key)}
    application = tornado.web.Application([
        (r"/{0,1}", RootHandler, resources),
        (r"/events/([0-9]+)/{0,1}", EventHandler, resources),
        (r"/schedule/([A-Za-z-_0-9]+)/{0,1}", ScheduleHandler, resources),
    ])
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
