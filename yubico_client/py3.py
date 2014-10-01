# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Libcloud Python 2.x and 3.x compatibility layer
# Some methods bellow are taken from Django PYK3 port which is licensed under 3
# clause BSD license
# https://bitbucket.org/loewis/django-3k

# Taken from Apache Libcloud which is license under the Apache 2.0 License
import sys

PY3 = False
PY2 = False
PY25 = False
PY27 = False
PY3 = False
PY32 = False

if sys.version_info >= (2, 0) and sys.version_info < (3, 0):
    PY2 = True

if sys.version_info >= (2, 5) and sys.version_info <= (2, 6):
    PY25 = True

if sys.version_info >= (2, 7) and sys.version_info <= (2, 8):
    PY27 = True

if sys.version_info >= (3, 0):
    PY3 = True

if sys.version_info >= (3, 2) and sys.version_info < (3, 3):
    PY32 = True

if PY3:
    from urllib.parse import urlencode as urlencode
    from urllib.parse import unquote as unquote

    u = str

    def b(s):
        if isinstance(s, str):
            return s.encode('utf-8')
        elif isinstance(s, bytes):
            return s
        else:
            raise TypeError("Invalid argument %r for b()" % (s,))
else:
    from urllib import urlencode as urlencode  # NOQA
    from urllib import unquote as unquote  # NOQA

    u = unicode
    b = bytes = str

if PY27 or PY3:
    unittest2_required = False
else:
    unittest2_required = True
