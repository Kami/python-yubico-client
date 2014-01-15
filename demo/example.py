import sys

from yubico_client import Yubico
from yubico_client import yubico_exceptions
from yubico_client.py3 import PY3

if PY3:
    raw_input = input

client_id = raw_input('Enter your client id: ')
secret_key = raw_input('Enter your secret key (optional): ')
token = raw_input('Enter OTP token: ')

if not secret_key:
    secret_key = None

client = Yubico(client_id, secret_key)

try:
    status = client.verify(token)
except yubico_exceptions.InvalidClientIdError:
    e = sys.exc_info()[1]
    print('Client with id %s does not exist' % (e.client_id))
    sys.exit(1)
except yubico_exceptions.SignatureVerificationError:
    print('Signature verification failed')
    sys.exit(1)
except yubico_exceptions.StatusCodeError:
    e = sys.exc_info()[1]
    print('Negative status code was returned: %s' % (e.status_code))
    sys.exit(1)

if status:
    print('Success, the provided OTP is valid')
else:
    print('No response from the servers or received other negative '
          'status code')
