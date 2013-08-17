Yubico Python Client
====================

.. image:: https://badge.fury.io/py/yubico-client.png
    :target: https://badge.fury.io/py/yubico-client

.. image:: https://secure.travis-ci.org/Kami/python-yubico-client.png?branch=master
        :target: http://travis-ci.org/Kami/python-yubico-client

.. image:: https://pypip.in/d/yubico-client/badge.png
        :target: https://crate.io/packages/yubico-client

Python class for verifying Yubico One Time Passwords (OTPs) based on the
validation protocol version 2.0.

* Yubico website: http://www.yubico.com
* Yubico documentation: http://www.yubico.com/developers/intro/
* Validation Protocol Version 2.0 FAQ: http://www.yubico.com/develop/open-source-software/web-api-clients/server/
* Validation Protocol Version 2.0 description: https://github.com/Yubico/yubikey-val/wiki/ValidationProtocolV20

For more information and usage examples, please see the.
`documentation <https://yubico-client.readthedocs.org/en/latest/>`_.

Documentation
-------------

Documentation is available at https://yubico-client.readthedocs.org/en/latest/

Installation
------------

.. code-block:: bash

    $ pip install yubico-client

Note: Package has been recently renamed from `yubico` to `yubico-client` and
the main module has been renamed from `yubico` to `yubico_client`. This
was done to avoid naming conflicts and make creation of distribution specific
packages easier.

Running Tests
-------------

To run the tests use the tox command. This will automatically run the tests on
all the supported Python versions.

.. code-block:: bash

    $ tox

License
-------

Yubico Client is distributed under the `3-Clause BSD License`_.

.. _`3-Clause BSD License`: http://opensource.org/licenses/BSD-3-Clause
