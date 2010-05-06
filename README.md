# Yubico Python Client

Python class for verifying Yubico One Time Passwords (OTPs) based on the validation protocol version 2.0.

* Yubico website: [http://www.yubico.com](http://www.yubico.com)
* Yubico documentation: [http://www.yubico.com/developers/intro/](http://www.yubico.com/developers/intro/)
* Validation Protocol Version 2.0 FAQ: [http://www.yubico.com/developers/version2/](http://www.yubico.com/developers/version2/)
* Validation Protocol Version 2.0 description: [http://code.google.com/p/yubikey-val-server-php/wiki/ValidationProtocolV20](http://code.google.com/p/yubikey-val-server-php/wiki/ValidationProtocolV20)

## Usage

1. Generate your client id and secret key (this can be done by visiting the [Yubico website](https://api.yubico.com/get-api-key/))
2. Use the client

    from yubico import Yubico
    
    yubico = Yubico('client id', 'secret key')
    yubico.verify('otp')

The **verify** method will return one of the following values:

- **True** - the provided OTP is valid (STATUS=OK)
- **None** - server returned one of the following status values: **BAD_OTP**, **BAD_SIGNATURE**, **MISSING_PARAMETER**, **NO_SUCH_CLIENT**, **OPERATION_NOT_ALLOWED**, **BACKEND_ERROR**, **NOT_ENOUGH_ANSWERS**, **REPLAYED_REQUEST** or no response was received from any of the servers in the specified time frame (default timeout = 10 seconds)

or raise one of the following exceptions:

- **StatusCodeError** - server returned **REPLAYED_OTP** status code
- **SignatureVerificationError** - server response message signature verification failed