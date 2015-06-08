#!/usr/bin/env python

import logging
import webapp2
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

import jinja2
import os

import askfm
import json
from google.appengine.api import memcache

import random

COOKIE_STORE_KEY = 'askfm_cookie_store'
COOKIE_MEMCACHE_TIMEOUT = 60*60*24*2 # 2 days

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

with open('phrases.txt') as f:
    ANSWER_PHRASES = f.read().splitlines()


def get_client_and_login():
    client = askfm.AskFmClient()
    cookies = memcache.get(COOKIE_STORE_KEY)

    # must log in again
    if cookies is None:
        # load credentials from file storagte
        with open('credentials') as f:
            credentials = json.loads(f.read())
        username = credentials['username']
        password = credentials['password']

        client.login(username, password)

        # save cookies for 1 day
        cookies = client._cookie_jar.output()
        success = memcache.add(COOKIE_STORE_KEY, cookies, COOKIE_MEMCACHE_TIMEOUT)

        logging.info("Cookies not in memcache, so logged in and stored: " + str(success))

    # already logged in
    else:
        client._cookie_jar.load(cookies)
        client.logged_in = True

    assert client.logged_in == True
    return client


def get_plaintext_body(mail_message):
    plaintext_bodies = list(mail_message.bodies('text/plain'))
    return plaintext_bodies[0][1].decode()


def get_response_to_question(question):
    return random.choice(ANSWER_PHRASES)
    #return u'RICH! You can afford a question of length {}.\n.format(
    #    len(question['question_text']))


def reply_to_all_questions(client, questions):
    replied_questions = []
    for question in reversed(questions):
        if not question['question_id']:
            continue

        answer_text = get_response_to_question(question)
        client.answer_question(question['question_id'], answer_text)

        question = dict(question) # create copy
        question['answer_text'] = answer_text
        replied_questions.append(question)
    return replied_questions


# Handles requests to /
class MainHandler(webapp2.RequestHandler):
    def get(self):
        client = get_client_and_login()
        questions = client.get_inbox_questions()

        template_values = {
            'questions': questions,
            'num_questions': len(questions),
        }
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

        logging.info('MainHandler: listed %d questions' % len(questions))

        """
        self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        self.response.write('Listing pending questions:\n')
        self.response.write('========\n\n')

        client = get_client_and_login()
        questions = client.get_inbox_questions()

        for question in questions:
            string = LIST_QUESTIONS_FORMAT.format(**question)
            self.response.write(string.encode('utf-8'))
        """


# Handles requests to /process_questions
class ProcessQuestionsHandler(webapp2.RequestHandler):
    def post(self):
        client = get_client_and_login()
        questions = client.get_inbox_questions()
        replied_questions = reply_to_all_questions(client, questions)

        template_values = {
            'replied_questions': replied_questions,
            'num_replied_questions': len(replied_questions),
        }

        template = JINJA_ENVIRONMENT.get_template('process_questions.html')
        self.response.write(template.render(template_values))

        logging.info('ProcessQuestionsHandler: replied to %d questions' % len(replied_questions))

        """
        self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        self.response.write('Replying to all questions:\n')
        client = get_client_and_login()
        questions = client.get_inbox_questions()
        replied_questions = reply_to_all_questions(client)

        for question in replied_questions:
            string = PROCESS_QUESTIONS_FORMAT.format(**question)
            self.response.write(string.encode('utf-8'))

        string = 'Replied to {:d} questions.'.format(len(replied_questions))
        self.response.write(string + '\n')
        logging.info('ProcessQuestionsHandler: ' + string)
        """


# Special handler for emails
class EmailHandler(InboundMailHandler):
    def receive(self, mail_message):
        string = u"Received email from: {}, to: {}, subject: {}".format(
            mail_message.sender, mail_message.to, mail_message.subject)
        logging.info(string.encode('utf-8'))

        body = get_plaintext_body(mail_message)
        logging.info("Body of email: " + body.encode('utf-8'))

        if 'noreply@ask.fm' not in mail_message.sender:
            logging.warn("Message not from ask.fm, ignoring.")
            return

        client = get_client_and_login()
        questions = client.get_inbox_questions()
        reply_to_all_questions(client, questions)


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/process_questions', ProcessQuestionsHandler)
], debug=True)

mailapp = webapp2.WSGIApplication([
    EmailHandler.mapping(),
], debug=True)
