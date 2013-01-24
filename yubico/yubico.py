# -*- coding: utf-8 -*-
#
# Name: Yubico Python Client
# Description: Python class for verifying Yubico One Time Passwords (OTPs).
#
# Author: Tomaž Muraus (http://www.tomaz.me)
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
import time
import urllib
import hmac
import base64
import hashlib
import threading
import logging

import requests

from otp import OTP
from yubico_exceptions import (StatusCodeError, InvalidClientIdError,
                               InvalidValidationResponse,
                               SignatureVerificationError)

logger = logging.getLogger('yubico.client')
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)

# Path to the custom CA certificates bundle. Only used if set.
CA_CERTS_BUNDLE_PATH = None

COMMON_CA_LOCATIONS = [
    '/usr/local/lib/ssl/certs/ca-certificates.crt',
    '/usr/local/ssl/certs/ca-certificates.crt',
    '/usr/local/share/curl/curl-ca-bundle.crt',
    '/usr/local/etc/openssl/cert.pem',
    '/opt/local/lib/ssl/certs/ca-certificates.crt',
    '/opt/local/ssl/certs/ca-certificates.crt',
    '/opt/local/share/curl/curl-ca-bundle.crt',
    '/opt/local/etc/openssl/cert.pem',
    '/usr/lib/ssl/certs/ca-certificates.crt',
    '/usr/ssl/certs/ca-certificates.crt',
    '/usr/share/curl/curl-ca-bundle.crt',
    '/etc/ssl/certs/ca-certificates.crt',
    '/etc/pki/tls/cert.pem',
    '/etc/pki/CA/cacert.pem',
    'C:\Windows\curl-ca-bundle.crt',
    'C:\Windows\ca-bundle.crt',
    'C:\Windows\cacert.pem'
]

API_URLS = ('api.yubico.com/wsapi/2.0/verify',
            'api2.yubico.com/wsapi/2.0/verify',
            'api3.yubico.com/wsapi/2.0/verify',
            'api4.yubico.com/wsapi/2.0/verify',
            'api5.yubico.com/wsapi/2.0/verify')

DEFAULT_TIMEOUT = 10            # How long to wait before the time out occurs
DEFAULT_MAX_TIME_WINDOW = 40    # How many seconds can pass between the first
                                # and last OTP generations so the OTP is
                                # still considered valid (only used in the
                                # multi mode) default is 5 seconds
                                # (40 / 0.125 = 5)

BAD_STATUS_CODES = ['BAD_OTP', 'REPLAYED_OTP', 'BAD_SIGNATURE',
                    'MISSING_PARAMETER', 'OPERATION_NOT_ALLOWED',
                    'BACKEND_ERROR', 'NOT_ENOUGH_ANSWERS',
                    'REPLAYED_REQUEST']


class Yubico(object):
    def __init__(self, client_id, key=None, use_https=True, verify_cert=True,
                 translate_otp=True):
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
        ca_bundle_path = self._get_ca_bundle_path()

        otp = OTP(otp, self.translate_otp)
        nonce = base64.b64encode(os.urandom(30), 'xz')[:25]
        query_string = self.generate_query_string(otp.otp, nonce, timestamp,
                                                  sl, timeout)
        request_urls = self.generate_request_urls()

        threads = []
        timeout = timeout or DEFAULT_TIMEOUT
        for url in request_urls:
            thread = URLThread('%s?%s' % (url, query_string), timeout,
                               self.verify_cert, ca_bundle_path)
            thread.start()
            threads.append(thread)

        # Wait for a first positive or negative response
        start_time = time.time()
        while threads and (start_time + timeout) > time.time():
            for thread in threads:
                if not thread.is_alive():
                    if thread.exception:
                        raise thread.exception
                    elif thread.response:
                        status = self.verify_response(thread.response,
                                                      otp.otp, nonce,
                                                      return_response)

                        if status:
                            if return_response:
                                return status
                            else:
                                return True
                    threads.remove(thread)
            time.sleep(0.1)

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
                message = 'More than one status= returned. Possible attack!'
                raise InvalidValidationResponse(message, response)

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

        if 'otp' in param_dict and param_dict['otp'] != otp:
            message = 'Unexpected OTP in response. Possible attack!'
            raise InvalidValidationResponse(message, response, param_dict)

        if 'nonce' in param_dict and param_dict['nonce'] != nonce:
            message = 'Unexpected nonce in response. Possible attack!'
            raise InvalidValidationResponse(message, response, param_dict)

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

        if sl is not None:
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

            if index != len(split_dict) - 1:
                query_string += '&'

        return (signature, query_string)

    def get_parameters_as_dictionary(self, query_string):
        """ Returns query string parameters as a dictionary. """
        dictionary = dict([parameter.split('=', 1) for parameter
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

    def _get_ca_bundle_path(self):
        """
        Return a path to the CA bundle which is used for verifying the hosts
        SSL certificate.
        """
        if CA_CERTS_BUNDLE_PATH:
            # User provided a custom path
            return CA_CERTS_BUNDLE_PATH

        for file_path in COMMON_CA_LOCATIONS:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return file_path

        return None


class URLThread(threading.Thread):
    def __init__(self, url, timeout, verify_cert, ca_bundle_path=None):
        super(URLThread, self).__init__()
        self.url = url
        self.timeout = timeout
        self.verify_cert = verify_cert
        self.ca_bundle_path = ca_bundle_path
        self.exception = None
        self.request = None
        self.response = None

    def run(self):
        logger.debug('Sending HTTP request to %s (thread=%s)' % (self.url,
                                                                 self.name))
        verify = self.verify_cert

        if self.ca_bundle_path is not None:
            verify = self.ca_bundle_path
            logger.debug('Using custom CA bunde: %s' % (self.ca_bundle_path))

        try:
            self.request = requests.get(url=self.url, timeout=self.timeout,
                                        verify=verify)
            self.response = self.request.content
        except requests.exceptions.SSLError, e:
            self.exception = e
            self.response = None
        except Exception, e:
            logger.error('Failed to retrieve response: ' + str(e))
            self.response = None

        args = (self.url, self.name, self.response)
        logger.debug('Received response from %s (thread=%s): %s' % args)
