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
        self.status_code = status_code

    def __str__(self):
        return ('Yubico server returned the following status code: %s' %
                (self.status_code))


class InvalidClientIdError(YubicoError):
    def __init__(self, client_id):
        self.client_id = client_id

    def __str__(self):
        return 'The client with ID %s does not exist' % (self.client_id)


class InvalidValidationResponse(YubicoError):
    def __init__(self, reason, response, parameters=None):
        self.reason = reason
        self.response = response
        self.parameters = parameters
        self.message = self.reason

    def __str__(self):
        return self.reason


class SignatureVerificationError(YubicoError):
    def __init__(self, generated_signature, response_signature):
        self.generated_signature = generated_signature
        self.response_signature = response_signature

    def __str__(self):
        return repr('Server response message signature verification failed' +
                    '(expected %s, got %s)' % (self.generated_signature,
                                               self.response_signature))
