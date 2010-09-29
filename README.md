# Yubico Python Client

Python class for verifying Yubico One Time Passwords (OTPs) based on the validation protocol version 2.0.

* Yubico website: [http://www.yubico.com](http://www.yubico.com)
* Yubico documentation: [http://www.yubico.com/developers/intro/](http://www.yubico.com/developers/intro/)
* Validation Protocol Version 2.0 FAQ: [http://www.yubico.com/developers/version2/](http://www.yubico.com/developers/version2/)
* Validation Protocol Version 2.0 description: [http://code.google.com/p/yubikey-val-server-php/wiki/ValidationProtocolV20](http://code.google.com/p/yubikey-val-server-php/wiki/ValidationProtocolV20)

## Usage

1. Generate your client id and secret key (this can be done by visiting the [Yubico website](https://api.yubico.com/get-api-key/))
2. Use the client

Single mode:

    from yubico.yubico import Yubico
    
    yubico = Yubico('client id', 'secret key')
    yubico.verify('otp')

Multi mode:

    from yubico.yubico import Yubico
    
    yubico = Yubico('client id', 'secret key')
    yubico.verify_multi(['otp 1', 'otp 2', 'otp 3'])

The **verify** method will return one of the following values:

- **True** - the provided OTP is valid (STATUS=OK)
- **None** - server returned one of the following status values: **BAD_OTP**, **BAD_SIGNATURE**, **MISSING_PARAMETER**, **OPERATION_NOT_ALLOWED**, **BACKEND_ERROR**, **NOT_ENOUGH_ANSWERS**, **REPLAYED_REQUEST** or no response was received from any of the servers in the specified time frame (default timeout = 10 seconds)

The **verify_multi** method will return one of the following values:

- **True** - the provided OTPs are valid (STATUS=OK)
- **False** - all the OTPs don't contain the same device id, validation of one of the OTPs failed or 5 seconds (default) has passed between the time when the first and the last OTP was generated

Both methods can also throw one of the following exceptions:

- **StatusCodeError** - server returned **REPLAYED_OTP** status code
- **SignatureVerificationError** - server response message signature verification failed
- **InvalidClientIdError** - client with the specified id does not exist (server returned **NO_SUCH_CLIENT** status code)

## Notes

If you are using secure connection (https) and want to validate the server certificate, you need to pass ``verify_cert = True`` argument when instantiating the yubico class and set ``CA_CERTS`` variable in the
``yubico/httplib_ssl.py`` file so it points to a file containing trusted CA certificates.

For a backward compatibility, ``verify_cert`` is set to ``False`` by default.
