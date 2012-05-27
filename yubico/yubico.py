# -*- coding: utf-8 -*-
#
# Name: Yubico Python Client
# Description: Python class for verifying Yubico One Time Passwords (OTPs).
#
# Author: Tomaž Muraus (http://www.tomaz-muraus.info)
# License: BSD
#
# Copyright (c) 2010, Tomaž Muraus
# Copyright (c) 2012, Yubico AB
# All rights reserved.
#
# Requirements:
# - Python >= 2.5

import re
import os
import sys
import time
import socket
import urllib
import urllib2
import hmac
import base64
import hashlib
import threading
import logging

from otp import OTP
from yubico_exceptions import *

try:
    import httplib_ssl
except ImportError:
    httplib_ssl = None

logger = logging.getLogger('face')
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)

API_URLS = ('api.yubico.com/wsapi/2.0/verify',
            'api2.yubico.com/wsapi/2.0/verify',
            'api3.yubico.com/wsapi/2.0/verify',
            'api4.yubico.com/wsapi/2.0/verify',
            'api5.yubico.com/wsapi/2.0/verify')

DEFAULT_TIMEOUT = 10            # How long to wait before the time out occurs
DEFAULT_MAX_TIME_WINDOW = 40    # How many seconds can pass between the first
                                # and last OTP generations so the OTP is
                                # still considered valid (only used in the multi
                                # mode) default is 5 seconds (40 / 0.125 = 5)

BAD_STATUS_CODES = ['BAD_OTP', 'REPLAYED_OTP', 'BAD_SIGNATURE',
                    'MISSING_PARAMETER', 'OPERATION_NOT_ALLOWED',
                    'BACKEND_ERROR', 'NOT_ENOUGH_ANSWERS',
                    'REPLAYED_REQUEST']


class Yubico():
    def __init__(self, client_id, key=None, use_https=True, verify_cert=False,
                 translate_otp=True):

        if use_https and not httplib_ssl:
            raise Exception('SSL support not available')

        if use_https and httplib_ssl and httplib_ssl.CA_CERTS == '':
            raise Exception('If you want to validate server certificate,'
                            ' you need to set CA_CERTS '
                            'variable in the httplib_ssl.py file pointing '
                            'to a file which contains a list of trusted CA '
                            'certificates')

        self.client_id = client_id
        self.key = base64.b64decode(key) if key is not None else None
        self.use_https = use_https
        self.verify_cert = verify_cert
        self.translate_otp = translate_otp

    def verify(self, otp, timestamp=False, sl=None, timeout=None,
               return_response=False):
        """
        Returns True is the provided OTP is valid,
        False if the REPLAYED_OTP status value is returned or the response
        message signature verification failed and None for the rest of the
        status values.
        """
        otp = OTP(otp, self.translate_otp)
        nonce = base64.b64encode(os.urandom(30), 'xz')[:25]
        query_string = self.generate_query_string(otp.otp, nonce, timestamp,
                                                  sl, timeout)
        request_urls = self.generate_request_urls()

        threads = []
        timeout = timeout or DEFAULT_TIMEOUT
        for url in request_urls:
            thread = URLThread('%s?%s' % (url, query_string), timeout,
                                          self.verify_cert)
            thread.start()
            threads.append(thread)

        # Wait for a first positive or negative response
        start_time = time.time()
        while threads and (start_time + timeout) > time.time():
            for thread in threads:
                if not thread.is_alive() and thread.response:
                    status = self.verify_response(thread.response,
                                                  otp.otp, nonce,
                                                  return_response)

                    if status:
                        if return_response:
                            return status
                        else:
                            return True
                    threads.remove(thread)

        # Timeout or no valid response received
        raise Exception('NO_VALID_ANSWERS')

    def verify_multi(self, otp_list=None, max_time_window=None, sl=None,
                     timeout=None):
        # Create the OTP objects
        otps = []
        for otp in otp_list:
            otps.append(OTP(otp, self.translate_otp))

        device_ids = set()
        for otp in otps:
            device_ids.add(otp.device_id)

        # Check that all the OTPs contain same device id
        if len(device_ids) != 1:
            raise Exception('OTPs contain different device ids')

        # Now we verify the OTPs and save the server response for each OTP.
        # We need the server response, to retrieve the timestamp.
        # It's possible to retrieve this value locally, without querying the
        # server but in this case, user would need to provide his AES key.
        for otp in otps:
            response = self.verify(otp.otp, True, sl, timeout,
                                  return_response=True)

            if not response:
                return False

            otp.timestamp = int(response['timestamp'])

        count = len(otps)
        delta = otps[count - 1].timestamp - otps[0].timestamp

        if max_time_window:
            max_time_window = (max_time_window / 0.125)
        else:
            max_time_window = DEFAULT_MAX_TIME_WINDOW

        if delta > max_time_window:
            raise Exception('More then %s seconds has passed between ' +
                            'generating the first and the last OTP.' %
                            (max_time_window * 0.125))

        return True

    def verify_response(self, response, otp, nonce, return_response=False):
        """
        Returns True if the OTP is valid (status=OK) and return_response=False,
        otherwise (return_response = True) it returns the server response as a
        dictionary.

        Throws an exception if the OTP is replayed, the server response message
        verification failed or the client id is invalid, returns False
        otherwise.
        """
        try:
            status = re.search(r'status=([A-Z0-9_]+)', response) \
                                 .groups()
            if len(status) > 1:
                raise InvalidValidationResponse('More than one status= returned. Possible attack!',
                                                response)
            status = status[0]
        except (AttributeError, IndexError):
            return False

        signature, parameters = \
            self.parse_parameters_from_response(response)

        # Secret key is specified, so we verify the response message
        # signature
        if self.key:
            generated_signature = \
                    self.generate_message_signature(parameters)

            # Signature located in the response does not match the one we
            # have generated
            if signature != generated_signature:
                raise SignatureVerificationError(generated_signature,
                                                 signature)
        param_dict = self.get_parameters_as_dictionary(parameters)

        if 'otp' in param_dict and param_dict['dict'] != otp:
            raise InvalidValidationResponse('Unexpected OTP in response. Possible attack!',
                                            response, param_dict)
        if 'nonce' in param_dict and param_dict['nonce'] != nonce:
            raise InvalidValidationResponse('Unexpected nonce in response. Possible attack!',
                                            response, param_dict)

        if status == 'OK':
            if return_response:
                return param_dict
            else:
                return True
        elif status == 'NO_SUCH_CLIENT':
            raise InvalidClientIdError(self.client_id)
        elif status == 'REPLAYED_OTP':
            raise StatusCodeError(status)

        return False

    def generate_query_string(self, otp, nonce, timestamp=False, sl=None,
                              timeout=None):
        """
        Returns a query string which is sent to the validation servers.
        """
        data = [('id', self.client_id),
                ('otp', otp),
                ('nonce', nonce)]

        if timestamp:
            data.append(('timestamp', '1'))

        if sl:
            if sl not in range(0, 101) and sl not in ['fast', 'secure']:
                raise Exception('sl parameter value must be between 0 and '
                                 '100 or string "fast" or "secure"')

            data.append(('sl', sl))

        if timeout:
            data.append(('timeout', timeout))

        query_string = urllib.urlencode(data)

        if self.key:
            hmac_signature = self.generate_message_signature(query_string)
            query_string += '&h=%s' % (hmac_signature.replace('+', '%2B'))

        return query_string

    def generate_message_signature(self, query_string):
        """
        Returns a HMAC-SHA-1 signature for the given query string.
        http://goo.gl/R4O0E
        """
        pairs = query_string.split('&')
        pairs = [pair.split('=') for pair in pairs]
        pairs_sorted = sorted(pairs)
        pairs_string = '&' . join(['=' . join(pair) for pair in pairs_sorted])

        digest = hmac.new(self.key, pairs_string, hashlib.sha1).digest()
        signature = base64.b64encode(digest)

        return signature

    def parse_parameters_from_response(self, response):
        """
        Returns a response signature and query string generated from the
        server response. 'h' aka signature argument is stripped from the
        returned query string.
        """
        split = [pair.strip() for pair in response.split('\n')
                 if pair.strip() != '']
        query_string = '&' . join(split)
        split_dict = self.get_parameters_as_dictionary(query_string)

        if 'h' in split_dict:
            signature = split_dict['h']
            del split_dict['h']
        else:
            signature = None

        query_string = ''
        for index, (key, value) in enumerate(split_dict.iteritems()):
            query_string += '%s=%s' % (key, value)

            if index != len(split_dict) -1:
                query_string += '&'

        return (signature, query_string)

    def get_parameters_as_dictionary(self, query_string):
        """ Returns query string parameters as a dictionary. """
        dictionary = dict([parameter.split('=', 1) for parameter \
                    in query_string.split('&')])

        return dictionary

    def generate_request_urls(self):
        """
        Returns a list of the API URLs.
        """
        urls = []
        for url in API_URLS:
            if self.use_https:
                url = 'https://%s' % (url)
            else:
                url = 'http://%s' % (url)
            urls.append(url)

        return urls


class URLThread(threading.Thread):
    def __init__(self, url, timeout, verify_cert):
        super(URLThread, self).__init__()
        self.url = url
        self.timeout = timeout
        self.verify_cert = verify_cert
        self.request = None
        self.response = None

        if int(sys.version[0]) == 2 and int(sys.version[2]) <= 5:
            self.is_alive = self.isAlive

    def run(self):
        logger.debug('Sending HTTP request to %s (thread=%s)' % (self.url,
                                                                 self.name))
        socket.setdefaulttimeout(self.timeout)

        if self.url.startswith('https') and self.verify_cert:
            handler = httplib_ssl.VerifiedHTTPSHandler()
            opener = urllib2.build_opener(handler)
            urllib2.install_opener(opener)

        try:
            self.request = urllib2.urlopen(self.url)
            self.response = self.request.read()
        except Exception:
            self.response = None

        logger.debug('Received response from %s (thread=%s): %s' % (self.url,
                                                               self.name,
                                                               self.response))
