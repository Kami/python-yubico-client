# -*- coding: utf-8 -*-
#
# Name: Yubico Python Client
# Description: Python class for verifying Yubico One Time Passwords (OTPs).
#
# Author: Tomaz Muraus (http://www.tomaz.me)
# License: BSD
#
# Copyright (c) 2010-2019, Tomaž Muraus
# Copyright (c) 2012, Yubico AB
# All rights reserved.

import re
import os
import sys
import time
import hmac
import base64
import hashlib
import threading
import logging

import requests

from yubico_client.otp import OTP
from yubico_client.yubico_exceptions import (StatusCodeError,
                                             InvalidClientIdError,
                                             InvalidValidationResponse,
                                             SignatureVerificationError)
from yubico_client.py3 import b
from yubico_client.py3 import urlencode
from yubico_client.py3 import unquote

logger = logging.getLogger('yubico.client')

# Path to the standard CA bundle file locations for most of the operating
# systems
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
    r'C:\Windows\curl-ca-bundle.crt',
    r'C:\Windows\ca-bundle.crt',
    r'C:\Windows\cacert.pem'
]

DEFAULT_API_URLS = ('https://api.yubico.com/wsapi/2.0/verify',
                    'https://api2.yubico.com/wsapi/2.0/verify',
                    'https://api3.yubico.com/wsapi/2.0/verify',
                    'https://api4.yubico.com/wsapi/2.0/verify',
                    'https://api5.yubico.com/wsapi/2.0/verify')

# How long to wait before the time out occurs
DEFAULT_TIMEOUT = 10

# How many seconds can pass between the first and last OTP generation so the
# OTP is still considered valid
DEFAULT_MAX_TIME_WINDOW = 5

BAD_STATUS_CODES = ['BAD_OTP', 'REPLAYED_OTP', 'BAD_SIGNATURE',
                    'MISSING_PARAMETER', 'OPERATION_NOT_ALLOWED',
                    'BACKEND_ERROR', 'NOT_ENOUGH_ANSWERS',
                    'REPLAYED_REQUEST']


class Yubico(object):
    def __init__(self, client_id, key=None, verify_cert=True,
                 translate_otp=True, api_urls=DEFAULT_API_URLS,
                 ca_certs_bundle_path=None):

        if ca_certs_bundle_path and \
           not self._is_valid_ca_bundle_file(ca_certs_bundle_path):
            raise ValueError('Invalid value provided for ca_certs_bundle_path'
                             ' argument')

        self.client_id = client_id

        if key is not None:
            key = base64.b64decode(key.encode('ascii'))

        self.key = key
        self.verify_cert = verify_cert
        self.translate_otp = translate_otp
        self.api_urls = self._init_request_urls(api_urls=api_urls)
        self.ca_certs_bundle_path = ca_certs_bundle_path

    def verify(self, otp, timestamp=False, sl=None, timeout=None,
               return_response=False):
        """
        Verify a provided OTP.

        :param otp: OTP to verify.
        :type otp: ``str``

        :param timestamp: True to include request timestamp and session counter
                          in the response. Defaults to False.
        :type timestamp: ``bool``

        :param sl: A value indicating percentage of syncing required by client.
        :type sl: ``int`` or ``str``

        :param timeout: Number of seconds to wait for sync responses.
        :type timeout: ``int``

        :param return_response: True to return a response object instead of the
                                status code. Defaults to False.
        :type return_response: ``bool``

        :return: True is the provided OTP is valid, False if the
        REPLAYED_OTP status value is returned or the response message signature
        verification failed and None for the rest of the status values.
        """
        ca_bundle_path = self._get_ca_bundle_path()

        otp = OTP(otp, self.translate_otp)
        rand_str = b(os.urandom(30))
        nonce = base64.b64encode(rand_str, b('xz'))[:25].decode('utf-8')
        query_string = self.generate_query_string(otp.otp, nonce, timestamp,
                                                  sl, timeout)

        threads = []
        timeout = timeout or DEFAULT_TIMEOUT
        for url in self.api_urls:
            thread = URLThread('%s?%s' % (url, query_string), timeout,
                               self.verify_cert, ca_bundle_path)
            thread.start()
            threads.append(thread)

        # Wait for a first positive or negative response
        start_time = time.time()
        # pylint: disable=too-many-nested-blocks
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
                            # pylint: disable=no-else-return
                            if return_response:
                                return status
                            else:
                                return True
                    threads.remove(thread)
            time.sleep(0.1)

        # Timeout or no valid response received
        raise Exception('NO_VALID_ANSWERS')

    def verify_multi(self, otp_list, max_time_window=DEFAULT_MAX_TIME_WINDOW,
                     sl=None, timeout=None):
        """
        Verify a provided list of OTPs.

        :param max_time_window: Maximum number of seconds which can pass
                                between the first and last OTP generation for
                                the OTP to still be considered valid.
        :type max_time_window: ``int``
        """

        # Create the OTP objects
        otps = []
        for otp in otp_list:
            otps.append(OTP(otp, self.translate_otp))

        if len(otp_list) < 2:
            raise ValueError('otp_list needs to contain at least two OTPs')

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

        # OTPs have an 8Hz timestamp counter so we need to divide it to get
        # seconds
        delta = delta / 8

        if delta < 0:
            raise Exception('delta is smaller than zero. First OTP appears to '
                            'be older than the last one')

        if delta > max_time_window:
            raise Exception('More than %s seconds have passed between '
                            'generating the first and the last OTP.' %
                            (max_time_window))

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
                logger.warn("signature mismatch for parameters=%r", parameters)
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
            if return_response:  # pylint: disable=no-else-return
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

        query_string = urlencode(data)

        if self.key:
            hmac_signature = self.generate_message_signature(query_string)
            hmac_signature = hmac_signature
            query_string += '&h=%s' % (hmac_signature.replace('+', '%2B'))

        return query_string

    def generate_message_signature(self, query_string):
        """
        Returns a HMAC-SHA-1 signature for the given query string.
        http://goo.gl/R4O0E
        """
        # split for sorting
        pairs = query_string.split('&')
        pairs = [pair.split('=', 1) for pair in pairs]
        pairs_sorted = sorted(pairs)
        pairs_string = '&' . join(['=' . join(pair) for pair in pairs_sorted])

        digest = hmac.new(self.key, b(pairs_string), hashlib.sha1).digest()
        signature = base64.b64encode(digest).decode('utf-8')

        return signature

    def parse_parameters_from_response(self, response):
        """
        Returns a response signature and query string generated from the
        server response. 'h' aka signature argument is stripped from the
        returned query string.
        """
        lines = response.splitlines()
        pairs = [line.strip().split('=', 1) for line in lines if '=' in line]
        pairs = sorted(pairs)
        signature = ([unquote(v) for k, v in pairs if k == 'h'] or [None])[0]
        # already quoted
        query_string = '&' . join([k + '=' + v for k, v in pairs if k != 'h'])

        return (signature, query_string)

    def get_parameters_as_dictionary(self, query_string):
        """ Returns query string parameters as a dictionary. """
        pairs = (x.split('=', 1) for x in query_string.split('&'))
        return dict((k, unquote(v)) for k, v in pairs)

    def _init_request_urls(self, api_urls):
        """
        Returns a list of the API URLs.
        """
        if not isinstance(api_urls, (str, list, tuple)):
            raise TypeError('api_urls needs to be string or iterable!')

        if isinstance(api_urls, str):
            api_urls = (api_urls,)

        api_urls = list(api_urls)

        for url in api_urls:
            if not url.startswith('http://') and \
               not url.startswith('https://'):
                raise ValueError('URL "%s" contains an invalid or missing'
                                 ' scheme' % (url))

        return list(api_urls)

    def _get_ca_bundle_path(self):
        """
        Return a path to the CA bundle which is used for verifying the hosts
        SSL certificate.
        """
        if self.ca_certs_bundle_path:
            # User provided a custom path
            return self.ca_certs_bundle_path

        # Return first bundle which is available
        for file_path in COMMON_CA_LOCATIONS:
            if self._is_valid_ca_bundle_file(file_path=file_path):
                return file_path

        return None

    def _is_valid_ca_bundle_file(self, file_path):
        return os.path.exists(file_path) and os.path.isfile(file_path)


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
            self.response = self.request.content.decode('utf-8')
        except requests.exceptions.SSLError:
            e = sys.exc_info()[1]
            self.exception = e
            self.response = None
        except Exception:  # pylint: disable=broad-except
            e = sys.exc_info()[1]
            logger.error('Failed to retrieve response: %s' % (str(e)))
            self.response = None

        args = (self.url, self.name, self.response)
        logger.debug('Received response from %s (thread=%s): %s' % (args))
