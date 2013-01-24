1.6.0 - in development:

* Allow user to specify a path to the CA bundle which is used for verifying the
  server SSL certificate by setting `CA_CERTS_BUNDLE_PATH` variable
* When selecting which CA bundle is used for verifying the server SSL
  certificate look for the bundle in some common locations. #10
* Drop support for Python 2.5
* Use `requests` library for performing HTTP requests and turn SSL cert
  verification on by default
* Avoid busy-looping (add time.sleep) when waiting for responses.
* Allow user to pass in value `0` for `sl` argument in `verify` and
  `verify_multi` method
* Throw an exception inside `verify` and `verify_multi` method if timeout has
  occurred or invalid status code is returned
* Add logging
