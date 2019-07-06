.. :changelog:

Changelog
=========

1.11.0 - 2019-07-06
-------------------

* Drop support for Python 2.6. #28
* Test the code and verify it works with the following Python versions:
  * Python 3.3
  * Python 3.4
  * Python 3.5
  * Python 3.6
  * Python 3.7
  * PyPy 2
  * PyPy 3 #28

1.10.0 - 2015-10-02
-------------------

* Fix compatibility issue with Python versions >= 3.0 <= 3.3 #22
* Pin ``requests`` dependency to the latest version (2.7) #25 #27

  Contribution by Wouter van Bommel, Vianney Carel.

* Make sure the query parameters are unquoted when parsing them from the
  response. #23

  Contribution by Tamás Gulácsi.

1.9.1 - 2014-02-05
------------------

* Fix Python 3 compatibility issue. #21

1.9.0 - 2014-01-16
------------------

* To discourage bad practices, remove ``use_https`` argument from the `Yubico`
  class constructor all together. Also update ``DEFAULT_API_URLS`` variable to
  contain full URLs with a scheme (e.g.
  ``https://api.yubico.com/wsapi/2.0/verify``).

  If a user wants to use a custom non-https URL or URLs, they can still do that
  by passing ``api_urls`` argument with custom non-https URLs to the
  constructor.

* Replace ``CA_CERTS_BUNDLE_PATH`` module level variable with a
  ``ca_certs_bundle_path`` argument which can be passed to the Yubico class
  constructor.

* Update ``requests`` dependency from ``1.2`` to ``2.2``.

1.8.0 - 2013-11-09
------------------

* Modify ``verify_multi`` method to throw if ``otp_list`` argument contains
  less than two items
* Modify ``max_time_window`` argument in the ``verify_multi`` method to be
  in seconds (#19)
* Modify ``verify_multi`` method to throw if delta between the first and last
  OTP timestamp is smaller than zero

* Allow user to pass ``api_urls`` argument to the ``Yubico`` class constructor.
  This argument can contain a list of API urls which are used to validate the
  token. https://github.com/Kami/python-yubico-client/pull/18

  Contributed by Dain Nilsson
* Depend on newer version (``1.2.3``) of the ``requests`` library.
* Update code and tests so they also work under Python 3.3

1.7.0 - 2013-04-06
------------------

* Change PyPi package name from ``yubico`` to ``yubico-client``.

  This was done to prevent naming collisions and make creation of distribution
  specific packages (e.g. debian packages) easier.

1.6.2 - 2013-04-02
------------------

* If there are multiple interpretations for a given OTP, first try to find the one
  which matches the input OTP. If the one is found, use the input OTP, otherwise
  use random interpretation. - https://github.com/Kami/python-yubico-client/issues/14

  Reported by Klas Lindfors

1.6.1 - 2013-03-19
------------------

* Only run ``logging.basicConfig`` when running tests so logging config isn't initialised
  on module import - https://github.com/Kami/python-yubico-client/pull/13

1.6.0 - 2013-01-24
------------------

* Allow user to specify a path to the CA bundle which is used for verifying the
  server SSL certificate by setting ``CA_CERTS_BUNDLE_PATH`` variable.
* When selecting which CA bundle is used for verifying the server SSL
  certificate look for the bundle in some common locations - https://github.com/Kami/python-yubico-client/pull/10
* Drop support for Python 2.5
* Use ``requests`` library for performing HTTP requests and turn SSL cert
  verification on by default
* Avoid busy-looping (add ``time.sleep``) when waiting for responses - https://github.com/Kami/python-yubico-client/pull/9
* Allow user to pass in value ``0`` for ``sl`` argument in ``verify`` and
  ``verify_multi`` method - https://github.com/Kami/python-yubico-client/pull/8
* Throw an exception inside ``verify`` and ``verify_multi`` method if timeout has
  occurred or invalid status code is returned - https://github.com/Kami/python-yubico-client/pull/7
* Improve response validation and of included, verify that ``otp`` and ``nonce``
  parameters in the response match one provided in the request - https://github.com/Kami/python-yubico-client/pull/7
* Add logging
