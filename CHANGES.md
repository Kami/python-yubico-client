1.7.0 - in development:

* Allow user to pass `api_urls` argument to the `Yubico` class constructor.
  This argument can contain a list of API urls which are used to validate the
  token. #18

  Contributed by Dain Nilsson

* Depend on newer version (`1.2.3` )of `requests` library.

1.6.3 - 2013-04-06:

* Change PyPi package name from `yubico` to `yubico-client`.

  This was done to prevent naming collisions and make creation of distribution
  specific packages (e.g. debian packages) easier.

1.6.2 - 2013-04-02:

* If there are multiple interpretations for a given OTP, first try to find the one
  which matches the input OTP. If the one is found, use the input OTP, otherwise
  use random interpretation. - https://github.com/Kami/python-yubico-client/issues/14

  Reported by Klas Lindfors

1.6.1 - 2013-03-19:

* Only run `logging.basicConfig` when running tests so logging config isn't initialised
  on module import - https://github.com/Kami/python-yubico-client/pull/13

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
