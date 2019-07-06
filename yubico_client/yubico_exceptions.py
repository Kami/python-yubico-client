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

__all___ = [
    'YubicoError',
    'StatusCodeError',
    'InvalidClientIdError',
    'InvalidValidationResponse',
    'SignatureVerificationError'
]


class YubicoError(Exception):
    """ Base class for Yubico related exceptions. """
    pass


class StatusCodeError(YubicoError):
    def __init__(self, status_code):
        super(StatusCodeError, self).__init__()
        self.status_code = status_code

    def __str__(self):
        return ('Yubico server returned the following status code: %s' %
                (self.status_code))


class InvalidClientIdError(YubicoError):
    def __init__(self, client_id):
        super(InvalidClientIdError, self).__init__()
        self.client_id = client_id

    def __str__(self):
        return 'The client with ID %s does not exist' % (self.client_id)


class InvalidValidationResponse(YubicoError):
    def __init__(self, reason, response, parameters=None):
        super(InvalidValidationResponse, self).__init__()
        self.reason = reason
        self.response = response
        self.parameters = parameters
        self.message = self.reason

    def __str__(self):
        return self.reason


class SignatureVerificationError(YubicoError):
    def __init__(self, generated_signature, response_signature):
        super(SignatureVerificationError, self).__init__()
        self.generated_signature = generated_signature
        self.response_signature = response_signature

    def __str__(self):
        return repr('Server response message signature verification failed'
                    '(expected %s, got %s)' % (self.generated_signature,
                                               self.response_signature))
