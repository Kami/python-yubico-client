# -*- coding: utf-8 -*-
#!/usr/bin/env python
import os
import re
from distutils.core import setup

version_re = re.compile(
    r'__version__ = (\(.*?\))')

cwd = os.path.dirname(os.path.abspath(__file__))
fp = open(os.path.join(cwd, 'yubico.py'))

version = None
for line in fp:
    match = version_re.search(line)
    if match:
        version = eval(match.group(1))
        break
else:
    raise Exception('Cannot find version in yubico.py')
fp.close()

setup(name = 'yubico',
	  version = '.' . join(map(str, version)),
	  description = 'Python Yubico Client',
	  author = 'Tomaž Muraus',
	  author_email = 'kami@k5-storitve.net',
	  license = 'GPL',
	  url = 'http://github.com/Kami/python-yubico-client/',
	  download_url = 'http://github.com/Kami/python-yubico-client/',
	  py_modules = ['yubico'],
	  provides = ['yubico'], 
	  
	  classifiers = [
		  'Development Status :: 4 - Beta',
		  'Environment :: Console',
		  'Intended Audience :: Developers',
		  'Intended Audience :: System Administrators',
		  'License :: OSI Approved :: GNU General Public License (GPL)',
		  'Operating System :: OS Independent',
		  'Programming Language :: Python',
		  'Topic :: Security',
		  'Topic :: Software Development :: Libraries :: Python Modules',
	],
)