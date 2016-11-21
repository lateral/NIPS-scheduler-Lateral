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

#FIXME be consistent: documents or events?


def document_to_card(document):
    # prepare LIP document object for use in tornado template
    meta = document['meta']
    authors = meta['authors'].split(', ')
    author_ids = meta['author_ids'].split(', ')
    result = dict(id=document['id'], meta=meta, authors=authors,
                  author_ids=author_ids)
    if 'similarity' in document:
        result['similarity'] = document['similarity']
    return result


class APIHandler(tornado.web.RequestHandler):

    def initialize(self, api):
        self.api = api

    def get_event(self, event_id):
        document = self.api.get_document(event_id)
        return document_to_card(document)

    def get_schedule_cards(self, user_id):
        # get preferences for the user
        prefs = self.api.get_users_preferences(user_id)
        event_ids = [pref['document_id'] for pref in prefs]
        # get all the documents, one by one
        cards = [self.get_event(event_id) for event_id in event_ids]
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
            self.set_cookie(COOKIE_NAME, self.user_id)  # FIXME check expiry in browser


class EventsHandler(UserHandler):

    def get(self):
        # get all the events
        documents = self.api.get_documents()
        event_cards = [document_to_card(document) for document in documents]
        # get the user's schedule
        schedule_cards = self.get_schedule_cards(self.user_id)
        self.render('events.html',
                    schedule_cards=schedule_cards,
                    event_cards=event_cards,
                    user_id=self.user_id)


class EventHandler(UserHandler):

    def get(self, event_id):
        event = self.get_event(event_id)
        # FIXME fetch the tags

        # fetch the similar talks
        related_events = self.api.get_documents_similar(
            event_id, fields='meta,text', exclude='[%s]' % event_id,
            number=NUM_RESULTS)
        related_events = map(document_to_card, related_events)
        # fetch the similar arxiv papers, include them
        related_papers = self.get_related_papers(event['meta']['abstract_text'])
        self.render('event.html', related_events=related_events, related_papers=related_papers, **event)

    def _respond_schedule(self):
        """
        respond with list of event ids preferenced, JSON encoded
        """
        prefs = self.api.get_users_preferences(self.user_id)
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
        schedule_cards = self.get_schedule_cards(user_id)
        self.render('printable_schedule.html', user_id=user_id,
                    schedule_cards=schedule_cards)


def build_application(key):
    resources = {'api': Api(key)}
    application = tornado.web.Application([
        (r"/{0,1}", EventsHandler, resources),
        (r"/([0-9]+)/{0,1}", EventHandler, resources),
        (r"/schedule/([A-Za-z-_0-9]+)/{0,1}", ScheduleHandler, resources),
        (r"/(.*\.css)", tornado.web.StaticFileHandler, {'path': './'}), # FIXME path
        (r"/(.*\.js)", tornado.web.StaticFileHandler, {'path': './'}), # FIXME path
    ], debug=True) # FIXME remove debug=True for deployment
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
