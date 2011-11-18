import sys
from yubico import yubico
from yubico import yubico_exceptions

client_id = raw_input('Enter your client id: ')
secret_key = raw_input('Enter your secret key (optional): ')
use_https = raw_input('Use secure connection (https)? [y/n]: ')
token = raw_input('Enter OTP token: ')

if not secret_key:
    secret_key = None

if use_https == 'n':
    https = False
else:
    https = True

client = yubico.Yubico(client_id, secret_key, https)

try:
    status = client.verify(token)
except yubico_exceptions.InvalidClientIdError, e:
    print 'Client with id %s does not exist' % (e.client_id)
    sys.exit(1)
except yubico_exceptions.SignatureVerificationError:
    print 'Signature verification failed'
    sys.exit(1)
except yubico_exceptions.StatusCodeError, e:
    print 'Negative status code was returned: %s' % (e.status_code)
    sys.exit(1)

if status:
    print 'Success, the provided OTP is valid'
else:
    print 'No response from the servers or received other negative status code'
