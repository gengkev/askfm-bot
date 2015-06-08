#!/usr/bin/env python2

import urllib2
from urllib import urlencode
from Cookie import SimpleCookie

import re
from bs4 import BeautifulSoup

import logging

USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.30 Safari/537.36"
ASK_FM_BASE = "http://ask.fm"

"""
class User(object):
    Anon = User('', '')
    def __init__(self, username, name):
        self.username = username
        self.name = name

    def __eq__(self, other):
        if type(other) is type(self):
            return self.name == other.name
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class Question(object):
    def __init__(self, text, recipient, author=User.Anon):
        self.text = text
        self.author = author
        self.recipient = recipient
"""

"""
class RequestHandler(urllib2.BaseHandler):
    def __init__(self, outer):
        self.outer = outer

    def http_request(self, req):
        cookie = self.outer._cookie_jar.output(attrs='', header='')
        req.add_header('User-Agent', USER_AGENT)
        req.add_header('Cookie', cookie)

    def http_response(self, req, resp):
        # put cookies into cookie jar
        cookies = resp.info().getheaders('set-cookie')
        for cookie_header in cookies:
            self.outer._cookie_jar.load(cookie_header)

        return resp
"""

class AskFmClient(object):
    def __init__(self):
        self.logged_in = False
        self.username = None
        self.password = None

        self._cookie_jar = SimpleCookie()
        self._saved_token = None

    """
    def _save_cookie_jar(self):
        with open('cookie_jar.txt', 'w') as f:
            cookies = self._cookie_jar.output()
            f.write(cookies)


    def _load_cookie_jar(self):
        with open('cookie_jar.txt', 'r') as f:
            cookies = f.read()
            self._cookie_jar.load(cookies)
    """

    def _get_token(self):
        # make request
        url = "http://ask.fm/"
        page = self._request(url)

        # find token in page
        match = re.search('var AUTH_TOKEN = "(.*)";', page)
        if not match:
            raise ValueError('No token found')

        token = match.group(1)
        logging.debug('.. got auth token: {}'.format(token))
        return token


    def _request(self, url, data=None, headers={}):
        logging.debug('.. Making request to {}'.format(url))
        req = urllib2.Request(url)

        # add data
        if data:
            #req.add_header('Content-Type', 'application/x-www-urlencoded')
            #req.add_header('Content-Length', len(data))
            req.add_data(data)

        # add cookies
        cookie = self._cookie_jar.output(attrs=[], header='', sep=',')
        req.add_header('Cookie', cookie)

        # add headers
        req.add_header('User-Agent', USER_AGENT)
        req.add_header('Referer', 'http://ask.fm/')
        for key in headers:
            req.add_header(key, headers[key])

        #print '.... sending cookie header', cookie

        # actually request
        resp = urllib2.urlopen(req)

        # save cookies
        cookies = resp.info().getheaders('set-cookie')
        for cookie_header in cookies:
            self._cookie_jar.load(cookie_header)
            #print '.... saving cookies', cookie_header

        page = resp.read()
        return page


    def login(self, username, password):
        if not username or not password:
            raise ValueError('Username or password is empty')
        if self.logged_in:
            raise ValueError('Cannot sign in when already signed in')

        logging.debug('>> Logging in')
        # make request
        url = "http://ask.fm/session"
        token = self._get_token()
        data = {
            'authenticity_token': token,
            'login': username,
            'password': password,
        }
        headers = {
            'X-Requested-With': 'XMLHttpRequest'
        }
        page = self._request(url, urlencode(data), headers=headers)

        # try to find incorrect
        success1 = page == 'window.location.href = "/";'
        success2 = 'Incorrect username or password' not in page

        if success1 != success2:
            logging.debug(page)
            raise ValueError('Sucess detection inconsistent')
        if not success1:
            raise ValueError('Incorrect username or password.')

        # save credentials
        self.logged_in = True
        self.username = username
        self.password = password


    def get_profile_questions(self, recipient):
        logging.debug('>> Getting profile questions')
        if not recipient:
            raise ValueError('Recipient is empty')
        # make request
        url = "http://ask.fm/{}".format(recipient)
        page = self._request(url)

        # try to find .questionBox
        soup = BeautifulSoup(page)
        questions = []
        for tag in soup.find_all(class_=re.compile('^questionBox')):
            # Question
            question_tag = tag.find(class_='question')
            if not question_tag: # skip if not found
                continue
            question_text = question_tag.span.get_text().strip()
            question_id = tag.get('id', '').replace('inbox_question_', '') or None

            # Author
            author_username = None
            author_name = None
            author_tag = question_tag.find(class_='author')
            if author_tag:
                author_username = author_tag.a['href'][1:]
                author_name = author_tag.a.get_text()

            # Answer, time
            answer_text = tag.find(class_='answer').get_text().strip()
            time_text = tag.find(class_='time').a.get_text()

            # Likes
            likes = 0
            like_tag = tag.find(_class='likeList people-like-block')
            if like_tag:
                likes = 0
                if like_tag.a:
                    likes = int(like_tag.a.get_text().replace(' person', ''))
                if like_tag['style'].trim() == 'display:none':
                    likes += 1 # this user also likes this

            questions.append({
                'question_id': question_id,
                'question_text': question_text,
                'author_username': author_username,
                'author_name': author_name,
                'answer_text': answer_text,
                'time': time_text,
                'likes': likes,
            })

        return questions


    def get_inbox_questions(self):
        logging.debug('>> Getting inbox questions')
        if not self.logged_in:
            raise ValueError('Not signed in')

        # make request
        url = "http://ask.fm/account/questions"
        page = self._request(url)

        # try to find .questionBox
        soup = BeautifulSoup(page)
        questions = []
        for tag in soup.find_all(class_=re.compile('^questionBox')):
            # Question
            question_tag = tag.find(class_='question')
            if not question_tag: # skip if not found
                continue
            question_text = question_tag.span.get_text().strip()
            question_id = tag.get('id', '').replace('inbox_question_', '') or None

            # Author
            author_username = None
            author_name = None
            author_tag = question_tag.find(class_='author')
            if author_tag:
                author_username = author_tag.a['href'][1:]
                author_name = author_tag.a.get_text()

            questions.append({
                'question_id': question_id,
                'question_text': question_text,
                'author_username': author_username,
                'author_name': author_name,
            })

        return questions


    def ask_question(self, recipient, question, anon=True):
        logging.debug('>> Asking question to: {}'.format(recipient))
        if not recipient or not question:
            raise ValueError('Recipient or question is empty')
        if not self.logged_in and not anon:
            raise ValueError('Not signed in')

        # make request
        url = "http://ask.fm/{}/questions/create".format(recipient)
        token = self._get_token()
        data = {
            'authenticity_token': token,
            'question[question_text]': question,
        }

        if self.logged_in and anon:
            data['question[force_anonymous]'] = 1

        page = self._request(url, urlencode(data))


    def answer_question(self, question_id, answer_text):
        logging.debug('>> Answering question: {}'.format(question_id))
        if not question_id or not answer_text:
            raise ValueError('Question ID or answer text is empty')
        if not self.logged_in:
            raise ValueError('Not signed in')

        # make request
        url = "http://ask.fm/questions/{}/answer".format(question_id)
        token = self._get_token()
        data = {
            'authenticity_token': token,
            'question[answer_text]': answer_text,
            'question[submit_stream]': 1,
            'question[submit_twitter]': 0,
            'question[submit_facebook]': 0,
            '_method': 'put',
            'commit': 'Answer',
        }
        page = self._request(url, urlencode(data))


    def delete_question(self, question_id):
        logging.debug('>> Deleting question: {}'.format(question_id))
        if not question_id:
            raise ValueError('Question ID is empty')
        if not self.logged_in:
            raise ValueError('Not signed in')

        # make request
        url = "http://ask.fm/questions/{}/delete".format(question_id)
        token = self._get_token()
        data = {
            'authenticity_token': token,
            '_method': 'delete',
        }
        page = self._request(url, urlencode(data))

