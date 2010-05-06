# -*- coding: utf-8 -*-
#
# Name: Yubico Python Client
# Description: Python class for verifying Yubico One Time Passwords (OTPs).
#
# This client is based on the Validation Protocol Version 2.0 so it sends
# the verification request to all the servers in parallel and it returns when
# the first positive (STATUS=OK) or negative (STATUS=REPLAYED_OTP)response is
# received.
#            
# Author: Tomaž Muraus (http://www.tomaz-muraus.info)
# License: GPL (http://www.gnu.org/licenses/gpl.html)
# Version: 1.1

# Requirements:
# - Python >= 2.5

__version__ = (1, 1, 'dev')

import os
import time
import urllib
import urllib2
import hmac
import base64
import hashlib
import threading

API_URLS = ('api.yubico.com/wsapi/2.0/verify',
			'api2.yubico.com/wsapi/2.0/verify',
			'api3.yubico.com/wsapi/2.0/verify',
			'api4.yubico.com/wsapi/2.0/verify',
			'api5.yubico.com/wsapi/2.0/verify')
TIMEOUT = 10 # How long to wait before the time out occurs

class Yubico():
	def __init__(self, client_id, key = None, use_https = True):
		self.client_id = client_id
		self.key = base64.b64decode(key) if key is not None else None
		self.use_https = use_https
	
	def verify(self, otp, timestamp = False, sl = None, timeout = None):
		"""
		Returns True is the provided OTP is valid,
		False if the REPLAYED_OTP status value is returned or the response
		message signature verification failed and None for the rest of the status values.
		"""
		nonce = base64.b64encode(os.urandom(30), 'xz')[:25]
		query_string = self.generate_query_string(otp, nonce, timestamp, sl, timeout)
		request_urls = self.generate_request_urls()

		threads = []
		timeout = timeout or TIMEOUT
		for url in request_urls:
			thread = URLThread('%s?%s' % (url, query_string), timeout)
			thread.start()
			threads.append(thread)

		# Wait for a first positive or negative response
		start_time = time.time()
		while threads and (start_time + timeout) > time.time():
			for thread in threads:
				if not thread.is_alive() and thread.response:
					status = self.verify_response(thread.response)
					
					if status:
						return True	
					threads.remove(thread)

		return None
				
	def verify_response(self, response):
		"""
		Returns 1 if the OTP is valid (status=OK), 2 if the OTP is replayed
		or the server response message verification failed, False otherwise.
		"""
		try:
			status = response.split('status=')[1].strip()

			# Secret key is specified, so we verify the response message
			# signature
			if self.key != None:
				signature, parameters = self.parse_parameters_from_response(response)
				generated_signature = self.generate_message_signature(parameters)
				
				# Signature located in the response does not match the one we have
				# generated
				if signature != generated_signature:
					raise SignatureVerificationError(generated_signature, signature)
		except KeyError:
			# Missing status code, malformed response?
			return False
		
		if status == 'OK':
			return True
		elif status == 'REPLAYED_OTP':
			raise StatusCodeError('REPLAYED_OTP')
		
		return False
		
	def generate_query_string(self, otp, nonce, timestamp = False, sl = None, timeout = None):
		"""
		Returns a query string which is sent to the validation servers.
		"""
		data = [('id', self.client_id),
				('otp', otp),
				('nonce', nonce)]
		
		if timestamp:
			data.append(('timestamp', '1'))
			
		if sl:
			if sl not in range(0,101) and sl not in ['fast', 'secure']:
				raise Exception('sl parameter value must be between 0 and 100 or string "fast" or "secure"')
			
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
		http://code.google.com/p/yubikey-val-server-php/wiki/ValidationProtocolV20
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
		Returns a response signature and query string generated from the server response.
		"""
		splitted = [pair.strip() for pair in response.split('\n') if pair.strip() != '']
		signature = splitted[0].replace('h=', '')
		query_string = '&' . join(splitted[1:])

		return (signature, query_string)
	
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
	def __init__(self, url, timeout):
		super(URLThread, self).__init__()
		self.url = url
		self.timeout = timeout
		self.request = None
		self.response = None
		
	def run(self):
		try:
			self.request = urllib2.urlopen(self.url, timeout = self.timeout)
			self.response = self.request.read()
		except Exception:
			self.response = None

class YubicoError(Exception):
	""" Base class for Yubico related exceptions. """
	pass

class StatusCodeError(YubicoError):
	def __init__(self, status_code):
		self.status_code = status_code
		
	def __str__(self):
		return 'Yubico server returned the following status code: %s' % (self.status_code)

class SignatureVerificationError(YubicoError):
	def __init__(self, generated_signature, response_signature):
		self.generated_signature = generated_signature
		self.response_signature = response_signature
		
	def __str__(self):
		return repr('Server response message signature verification failed (expected %s, got %s)' \
				% (self.generated_signature, self.response_signature))