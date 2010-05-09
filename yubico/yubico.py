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
# Version: 1.2

# Requirements:
# - Python >= 2.5

import os
import time
import urllib
import urllib2
import hmac
import base64
import hashlib
import threading

from otp import OTP
from yubico_exceptions import *

API_URLS = ('api.yubico.com/wsapi/2.0/verify',
			'api2.yubico.com/wsapi/2.0/verify',
			'api3.yubico.com/wsapi/2.0/verify',
			'api4.yubico.com/wsapi/2.0/verify',
			'api5.yubico.com/wsapi/2.0/verify')
TIMEOUT = 10 			# How long to wait before the time out occurs
MAX_TIME_WINDOW = 40	# How many seconds can pass between the first and last OTP generations
						# so the OTP is still considered valid (only used in the multi mode)
						# default is 5 seconds (40 / 0.125 = 5)

class Yubico():
	def __init__(self, client_id, key = None, use_https = True):
		self.client_id = client_id
		self.key = base64.b64decode(key) if key is not None else None
		self.use_https = use_https
	
	def verify(self, otp, timestamp = False, sl = None, timeout = None, return_response = False):
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
					status = self.verify_response(thread.response, return_response)
					
					if status:
						if return_response:
							return status
						else:
							return True	
					threads.remove(thread)

		return None
	
	def verify_multi(self, otp_list = None, max_time_window = None, sl = None, timeout = None):
		# Create the OTP objects
		otps = []
		for otp in otp_list:
			otps.append(OTP(otp))
		
		device_ids = set()
		for otp in otps:
			device_ids.add(otp.device_id)
			
		# Check that all the OTPs contain same device id
		if len (device_ids) != 1:
			return False
		
		# Now we verify the OTPs and save the server response for each OTP.
		# We need the server response, to retrieve the timestamp.
		# It's possible to retrieve this value locally, without querying the server
		# but in this case, user would need to provide his AES key.
		for otp in otps:
			response = self.verify(otp.otp, True, sl, timeout, return_response = True)
			
			if not response:
				return False

			otp.timestamp = int(response['timestamp'])
		
		count = len(otps)
		delta = otps[count - 1].timestamp - otps[0].timestamp
		
		max_time_window = (max_time_window / 0.125) if max_time_window else None
		max_time_window = max_time_window or MAX_TIME_WINDOW
		if delta > max_time_window:
			return False
		
		return True
				
	def verify_response(self, response, return_response = False):
		"""
		Returns True if the OTP is valid (status=OK) and return_response = False,
		otherwise (return_response = True) it returns the server response as a dictionary.
		
		Throws an exception if the OTP is replayed, the server response message
		verification failed or the client id is invalid, returns False otherwise.
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
			if return_response:
				query_string = self.parse_parameters_from_response(response)[1]
				response = self.get_parameters_as_dictionary(query_string)
				
				return response
			else:
				return True
		elif status == 'NO_SUCH_CLIENT':
			raise InvalidClientIdError(self.client_id)
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
	
	def get_parameters_as_dictionary(self, query_string):
		""" Returns query string parameters as a dictionary. """
		dictionary = dict([parameter.split('=') for parameter \
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