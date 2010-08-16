#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
from distutils.core import setup

version_re = re.compile(
    r'__version__ = (\(.*?\))')

cwd = os.path.dirname(os.path.abspath(__file__))
fp = open(os.path.join(cwd, 'yubico', '__init__.py'))

version = None
for line in fp:
    match = version_re.search(line)
    if match:
        version = eval(match.group(1))
        break
else:
    raise Exception('Cannot find version in __init__.py')
fp.close()

setup(name = 'yubico',
	  version = '.' . join(map(str, version)),
	  description = 'Python Yubico Client',
	  author = 'Tomaž Muraus',
	  author_email = 'kami@k5-storitve.net',
	  license = 'BSD',
	  url = 'http://github.com/Kami/python-yubico-client/',
	  download_url = 'http://github.com/Kami/python-yubico-client/downloads/',
	  packages = ['yubico'],
	  provides = ['yubico'],
	  
	  classifiers = [
		  'Development Status :: 4 - Beta',
		  'Environment :: Console',
		  'Intended Audience :: Developers',
		  'Intended Audience :: System Administrators',
		  'License :: OSI Approved :: BSD License',
		  'Operating System :: OS Independent',
		  'Programming Language :: Python',
		  'Topic :: Security',
		  'Topic :: Software Development :: Libraries :: Python Modules',
	],
)