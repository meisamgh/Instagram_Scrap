#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 10 11:48:31 2022

@author: meisamghafary
"""
import time
import requests
import re
import json
import hashlib
import os
from slugify import slugify
from session_manager import CookieSessionManager
from exception.instagram_auth_exception import InstagramAuthException
from exception.instagram_exception import InstagramException
import endpoints
from two_step_verification.console_verification import ConsoleVerification

class Instagram:
    HTTP_NOT_FOUND = 404
    HTTP_OK = 200
    HTTP_FORBIDDEN = 403
    HTTP_BAD_REQUEST = 400

    MAX_COMMENTS_PER_REQUEST = 300
    MAX_LIKES_PER_REQUEST = 50
    # 30 mins time limit on operations that require multiple self.__req
    PAGING_TIME_LIMIT_SEC = 1800
    PAGING_DELAY_MINIMUM_MICROSEC = 1000000  # 1 sec min delay to simulate browser
    PAGING_DELAY_MAXIMUM_MICROSEC = 3000000  # 3 sec max delay to simulate browser

    instance_cache = None

    def __init__(self, sleep_between_requests=0):
        self.__req = requests.session()
        self.paging_time_limit_sec = Instagram.PAGING_TIME_LIMIT_SEC
        self.paging_delay_minimum_microsec = Instagram.PAGING_DELAY_MINIMUM_MICROSEC
        self.paging_delay_maximum_microsec = Instagram.PAGING_DELAY_MAXIMUM_MICROSEC

        self.session_username = None
        self.session_password = None
        self.user_session = None
        self.rhx_gis = None
        self.sleep_between_requests = sleep_between_requests
        self.user_agent = 'Instagram 126.0.0.25.121 Android (23/6.0.1; 320dpi; 720x1280; samsung; SM-A310F; a3xelte; samsungexynos7580; en_GB; 110937453)'

    def with_credentials(self, username, password, session_folder=None):
        """
        param string username
        param string password
        param null sessionFolder

        return Instagram
        """
        Instagram.instance_cache = None

        if not session_folder:
            cwd = os.getcwd()
            session_folder = cwd + os.path.sep + 'sessions' + os.path.sep

        if isinstance(session_folder, str):

            Instagram.instance_cache = CookieSessionManager(session_folder, slugify(username) + '.txt')

        else:
            Instagram.instance_cache = session_folder

        Instagram.instance_cache.empty_saved_cookies()


        self.session_username = username
        self.session_password = password

    def set_proxies(self, proxy):
        if proxy and isinstance(proxy, dict):
            self.__req.proxies = proxy

    def disable_verify(self):
        self.__req.verify = False

    def disable_proxies(self):
        self.__req.proxies = {}

    def get_user_agent(self):
        return self.user_agent

    def set_user_agent(self, user_agent):
        self.user_agent = user_agent

    @staticmethod
    def set_account_medias_request_count(count):
        """
        Set how many media objects should be retrieved in a single request
        param int count
        """
        endpoints.request_media_count = count
    def generate_headers(self, session, gis_token=None):

        headers = {}
        if session is not None:
            cookies = ''
    
            for key in session.keys():
                cookies += f"{key}={session[key]}; "
    
            csrf = session['x-csrftoken'] if session['csrftoken'] is None else \
                session['csrftoken']
    
            headers = {
                'cookie': cookies,
                'referer': endpoints.BASE_URL + '/',
                'x-csrftoken': csrf
            }
    
        if self.user_agent is not None:
            headers['user-agent'] = self.user_agent
    
            if gis_token is not None:
                headers['x-instagram-gis'] = gis_token
    
        return headers

    def __generate_gis_token(self, variables):
        """
        :param variables: a dict used to  generate_gis_token
        :return: a token used to be verified by instagram
        """
        rhx_gis = self.__get_rhx_gis() if self.__get_rhx_gis() is not None else 'NULL'
        string_to_hash = ':'.join([rhx_gis, json.dumps(variables, separators=(',', ':')) if isinstance(variables, dict) else variables])
        return hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()

    def __get_rhx_gis(self):
        """
        :return: a string to generate gis_token
        """
        if self.rhx_gis is None:
            try:
                shared_data = self.__get_shared_data_from_page()
            except Exception as _:
                raise InstagramException('Could not extract gis from page')

            if 'rhx_gis' in shared_data.keys():
                self.rhx_gis = shared_data['rhx_gis']
            else:
                self.rhx_gis = None

        return self.rhx_gis

    def __get_mid(self):
        """manually fetches the machine id from graphQL"""
        time.sleep(self.sleep_between_requests)
        response = self.__req.get('https://www.instagram.com/web/__mid/')

        if response.status_code != Instagram.HTTP_OK:
            raise InstagramException.default(response.text,
                                             response.status_code)
    
        return response.text

    def is_logged_in(self, session):
        """
        :param session: session dict
        :return: bool
        """
        if session is None or 'sessionid' not in session.keys():
            return False

        session_id = session['sessionid']
        csrf_token = session['csrftoken']

        headers = {
            'cookie': f"ig_cb=1; csrftoken={csrf_token}; sessionid={session_id};",
            'referer': endpoints.BASE_URL + '/',
            'x-csrftoken': csrf_token,
            'X-CSRFToken': csrf_token,
            'user-agent': self.user_agent,
        }

        time.sleep(self.sleep_between_requests)
        response = self.__req.get(endpoints.BASE_URL, headers=headers)

        if not response.status_code == Instagram.HTTP_OK:
            return False

        cookies = response.cookies.get_dict()

        if cookies is None or not 'ds_user_id' in cookies.keys():
            return False

        return True

    def login(self, force=False, two_step_verificator=None):
        """support_two_step_verification true works only in cli mode - just run login in cli mode - save cookie to file and use in any mode
        :param force: true will refresh the session
        :param two_step_verificator: true will need to do verification when an account goes wrong
        :return: headers dict
        """
        if self.session_username is None or self.session_password is None:
            raise InstagramAuthException("User credentials not provided")

        if two_step_verificator:
            two_step_verificator = ConsoleVerification()

        session = json.loads(
            Instagram.instance_cache.get_saved_cookies()) if Instagram.instance_cache.get_saved_cookies() != None else None

        # if force or not self.is_logged_in(session):
        #     time.sleep(self.sleep_between_requests)
        #     response = self.__req.get(endpoints.BASE_URL)
        #     if not response.status_code == Instagram.HTTP_OK:
        #         raise InstagramException.default(response.text,
        #                                          response.status_code)

        #     match = re.findall(r'"csrf_token":"(.*?)"', response.text)

        #     if len(match) > 0:
        #         csrfToken = match[0]

        #     cookies = response.cookies.get_dict()

        #     # cookies['mid'] doesnt work at the moment so fetch it with function
        #     mid = self.__get_mid()

        #     headers = {
        #         'cookie': f"ig_cb=1; csrftoken={csrfToken}; mid={mid};",
        #         'referer': endpoints.BASE_URL + '/',
        #         'x-csrftoken': csrfToken,
        #         'X-CSRFToken': csrfToken,
        #         'user-agent': self.user_agent,
        #     }
        #     payload = {'username': self.session_username,
        #                'enc_password': f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{self.session_password}"}
        #     response = self.__req.post(endpoints.LOGIN_URL, data=payload,
        #                                headers=headers)

        #     if not response.status_code == Instagram.HTTP_OK:
        #         if (
        #                 response.status_code == Instagram.HTTP_BAD_REQUEST
        #                 and response.text is not None
        #                 and response.json()['message'] == 'checkpoint_required'
        #                 and two_step_verificator is not None):
        #             response = self.__verify_two_step(response, cookies,
        #                                               two_step_verificator)
        #             print('checkpoint required')

        #         elif response.status_code is not None and response.text is not None:
        #             raise InstagramAuthException(
        #                 f'Response code is {response.status_code}. Body: {response.text} Something went wrong. Please report issue.',
        #                 response.status_code)
        #         else:
        #             raise InstagramAuthException(
        #                 'Something went wrong. Please report issue.',
        #                 response.status_code)
        #     elif not response.json()['authenticated']:
        #         raise InstagramAuthException('User credentials are wrong.')

        #     cookies = response.cookies.get_dict()

        #     cookies['mid'] = mid
        #     Instagram.instance_cache.set_saved_cookies(json.dumps(cookies, separators=(',', ':')))

        #     self.user_session = cookies

        # else:
        self.user_session = session

        return self.generate_headers(self.user_session)

    def __verify_two_step(self, response, cookies, two_step_verificator):
        """
        :param response: Response object returned by Request
        :param cookies: user cookies
        :param two_step_verificator: two_step_verification instance
        :return: Response
        """
        new_cookies = response.cookies.get_dict()
        cookies = {**cookies, **new_cookies}

        cookie_string = ''
        for key in cookies.keys():
            cookie_string += f'{key}={cookies[key]};'

        headers = {
            'cookie': cookie_string,
            'referer': endpoints.LOGIN_URL,
            'x-csrftoken': cookies['csrftoken'],
            'user-agent': self.user_agent,
        }

        url = endpoints.BASE_URL + response.json()['checkpoint_url']

        time.sleep(self.sleep_between_requests)
        response = self.__req.get(url, headers=headers)
        data = Instagram.extract_shared_data_from_body(response.text)

        if data is not None:
            try:
                choices = \
                    data['entry_data']['Challenge'][0]['extraData']['content'][
                        3]['fields'][0]['values']
            except KeyError:
                choices = dict()
                try:
                    fields = data['entry_data']['Challenge'][0]['fields']
                    try:
                        choices.update({'label': f"Email: {fields['email']}",
                                        'value': 1})
                    except KeyError:
                        pass
                    try:
                        choices.update(
                            {'label': f"Phone: {fields['phone_number']}",
                             'value': 0})
                    except KeyError:
                        pass

                except KeyError:
                    pass

            if len(choices) > 0:
                selected_choice = two_step_verificator.get_verification_type(
                    choices)
                response = self.__req.post(url,
                                           data={'choice': selected_choice},
                                           headers=headers)

        if len(re.findall('"input_name":"security_code"', response.text)) <= 0:
            raise InstagramAuthException(
                'Something went wrong when try '
                'two step verification. Please report issue.',
                response.status_code)

        security_code = two_step_verificator.get_security_code()

        post_data = {
            'csrfmiddlewaretoken': cookies['csrftoken'],
            'verify': 'Verify Account',
            'security_code': security_code,
        }
        response = self.__req.post(url, data=post_data, headers=headers)
        if not response.status_code == Instagram.HTTP_OK \
                or 'Please check the code we sent you and try again' in response.text:
            raise InstagramAuthException(
                'Something went wrong when try two step'
                ' verification and enter security code. Please report issue.',
                response.status_code)

        return response
    def extract_shared_data_from_body(body):
        """
        :param body: html string from a page
        :return: a dict extract from page
        """
        array = re.findall(r'_sharedData = .*?;</script>', body)
        if len(array) > 0:
            raw_json = array[0][len("_sharedData ="):-len(";</script>")]

            return json.loads(raw_json)

        return None


class InstagramAuthException(Exception):
    def __init__(self, message = "", code = 401):
        super().__init__(f'{message}, Code:{code}')

class InstagramException(Exception):
    def __init__(self, message="", code=500):
        super().__init__(f'{message}, Code:{code}')
    
    @staticmethod
    def default(response_text, status_code):
        return InstagramException(
            'Response code is {status_code}. Body: {response_text} '
            'Something went wrong. Please report issue.'.format(
                response_text=response_text, status_code=status_code),
            status_code)

class InstagramNotFoundException(Exception):
    def __init__(self, message="", code=404):
        super().__init__(f'{message}, Code:{code}')


class CookieSessionManager:
    def __init__(self, session_folder, filename):
        self.session_folder = session_folder
        self.filename = filename

    def get_saved_cookies(self):
        try:
            f = open(self.session_folder + self.filename, 'r') 
            return f.read()
        except FileNotFoundError:
            return None

    def set_saved_cookies(self, cookie_string):
        if not os.path.exists(self.session_folder):
            os.makedirs(self.session_folder)

        with open(self.session_folder + self.filename,"w+") as f:
            f.write(cookie_string)

    def empty_saved_cookies(self):
        try:
            os.remove(self.session_folder + self.filename)
        except FileNotFoundError:
            pass
