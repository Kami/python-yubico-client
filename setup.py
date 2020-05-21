#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Name: Yubico Python Client
# Description: Python class for verifying Yubico One Time Passwords (OTPs).
#
# Author: Tomaz Muraus (http://www.tomaz.me)
# License: BSD
#
# Copyright (c) 2010-2019, Tomaž Muraus
# Copyright (c) 2012, Yubico AB
# All rights reserved.

import os
import re
import sys
import logging

from glob import glob
from os.path import splitext, basename, join as pjoin
from unittest import TextTestRunner, TestLoader

from distutils.core import Command
from setuptools import setup

sys.path.insert(0, pjoin(os.path.dirname(__file__)))

TEST_PATHS = ['tests']

version_re = re.compile(
    r'__version__ = (\(.*?\))')

cwd = os.path.dirname(os.path.abspath(__file__))

version = None
with open(os.path.join(cwd, 'yubico_client', '__init__.py')) as fp:
    for line in fp:
        match = version_re.search(line)
        if match:
            version = eval(match.group(1))  # pylint: disable=eval-used
            break

if not version:
    raise Exception('Cannot find version in __init__.py')


class TestCommand(Command):
    description = 'run test suite'
    user_options = []

    log_paths = []

    # Set to False to preserve mock server log files even if the tests succeed
    delete_mock_server_logs_on_success = True

    def initialize_options(self):
        FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
        logging.basicConfig(format=FORMAT)

        THIS_DIR = os.path.abspath(os.path.split(__file__)[0])
        sys.path.insert(0, THIS_DIR)
        for test_path in TEST_PATHS:
            sys.path.insert(0, pjoin(THIS_DIR, test_path))
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        self._run_mock_api_server()
        succeeded = self._run_tests()
        status_code = 0 if succeeded else 1

        if succeeded and self.delete_mock_server_logs_on_success:
            # On success we delete mock server log files
            for file_path in self.log_paths:
                if not os.path.isfile(file_path):
                    continue

                os.unlink(file_path)

        sys.exit(status_code)

    def _run_tests(self):
        testfiles = []
        for test_path in TEST_PATHS:
            for t in glob(pjoin(self._dir, test_path, 'test_*.py')):
                testfiles.append('.'.join(
                    [test_path.replace('/', '.'), splitext(basename(t))[0]]))

        tests = TestLoader().loadTestsFromNames(testfiles)

        t = TextTestRunner(verbosity=2)
        res = t.run(tests)
        return res.wasSuccessful()

    def _run_mock_api_server(self):
        # pylint: disable=import-outside-toplevel
        from test_utils.process_runners import TCPProcessRunner

        script = pjoin(os.path.dirname(__file__), 'tests/mock_http_server.py')

        for port in [8881, 8882, 8883]:
            args = [script, '--port=%s' % (port)]
            log_path = 'mock_api_server_%s.log' % (port)
            wait_for_address = ('127.0.0.1', port)
            server = TCPProcessRunner(args=args,
                                      wait_for_address=wait_for_address,
                                      log_path=log_path)
            server.setUp()
            self.log_paths.append(log_path)


with open('CHANGES.rst') as fp:
    CHANGELOG = fp.read()


setup(
    name='yubico-client',
    version='.' . join(map(str, version)),
    description='Library for verifying Yubikey One Time Passwords (OTPs)',
    long_description=open('README.rst').read() + '\n\n' + CHANGELOG,
    author='Tomaz Muraus',
    author_email='tomaz+pypi@tomaz.me',
    license='BSD',
    url='https://github.com/Kami/python-yubico-client/',
    download_url='https://github.com/Kami/python-yubico-client/releases',
    packages=['yubico_client'],
    provides=['yubico_client'],
    install_requires=[
        'requests>=2.7,<3.0',
    ],
    cmdclass={
        'test': TestCommand,
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Security',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
