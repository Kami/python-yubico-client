# Yubico Python Client

Python class for verifying Yubico One Time Passwords (OTPs) based on the
validation protocol version 2.0.

* Yubico website: [http://www.yubico.com][1]
* Yubico documentation: [http://www.yubico.com/developers/intro/][2]
* Validation Protocol Version 2.0 FAQ: [http://www.yubico.com/developers/version2/][3]
* Validation Protocol Version 2.0 description: [http://code.google.com/p/yubikey-val-server-php/wiki/ValidationProtocolV20][4]

## Installation

`pip install yubico`

## Build Status

[![Build Status](https://secure.travis-ci.org/Kami/python-yubico-client.png)](http://travis-ci.org/Kami/python-yubico-client)

## Running Tests

`python setup.py test`

## Usage

1. Generate your client id and secret key (this can be done by visiting the
   [Yubico website](https://api.yubico.com/get-api-key/))
2. Use the client

Single mode:

    from yubico.yubico import Yubico

    yubico = Yubico('client id', 'secret key')
    yubico.verify('otp')

Multi mode:

    from yubico.yubico import Yubico

    yubico = Yubico('client id', 'secret key')
    yubico.verify_multi(['otp 1', 'otp 2', 'otp 3'])

The **verify** method will return `True` if the provided OTP is valid
(STATUS=OK).

The **verify_multi** method will return `True` if all of the provided OTPs are
valid (STATUS=OK).

Both methods can also throw one of the following exceptions:

- **StatusCodeError** - server returned **REPLAYED_OTP** status code
- **SignatureVerificationError** - server response message signature
  verification failed
- **InvalidClientIdError** - client with the specified id does not exist
  (server returned **NO_SUCH_CLIENT** status code)
- **Exception** - server returned one of the following status values:
  **BAD_OTP**, **BAD_SIGNATURE**, **MISSING_PARAMETER**,
  **OPERATION_NOT_ALLOWED**, **BACKEND_ERROR**, **NOT_ENOUGH_ANSWERS**,
  **REPLAYED_REQUEST** or no response was received from any of the servers
  in the specified time frame (default timeout = 10 seconds)

[1]: http://www.yubico.com
[2]: http://www.yubico.com/developers/intro/
[3]: http://www.yubico.com/developers/version2/
[4]: http://code.google.com/p/yubikey-val-server-php/wiki/ValidationProtocolV20
