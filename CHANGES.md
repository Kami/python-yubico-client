1.6.0 - 2013-01-24:

* Allow user to specify a path to the CA bundle which is used for verifying the
  server SSL certificate by setting `CA_CERTS_BUNDLE_PATH` variable.
* When selecting which CA bundle is used for verifying the server SSL
  certificate look for the bundle in some common locations - https://github.com/Kami/python-yubico-client/pull/10
* Drop support for Python 2.5
* Use `requests` library for performing HTTP requests and turn SSL cert
  verification on by default
* Avoid busy-looping (add time.`sleep`) when waiting for responses - https://github.com/Kami/python-yubico-client/pull/9
* Allow user to pass in value `0` for `sl` argument in `verify` and
  `verify_multi` method - https://github.com/Kami/python-yubico-client/pull/8
* Throw an exception inside `verify` and `verify_multi` method if timeout has
  occurred or invalid status code is returned - https://github.com/Kami/python-yubico-client/pull/7
* Improve response validation and of included, verify that `otp` and `nonce` 
  parameters in the response match one provided in the request - https://github.com/Kami/python-yubico-client/pull/7
* Add logging
