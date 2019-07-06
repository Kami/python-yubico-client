#!/usr/bin/env python

import os
import time
import sys

try:
    import BaseHTTPServer
    BaseHTTPRequestHandler = BaseHTTPServer.BaseHTTPRequestHandler
    server_class = BaseHTTPServer.HTTPServer
except ImportError:
    from http.server import HTTPServer as BaseHTTPServer
    from http.server import BaseHTTPRequestHandler
    server_class = BaseHTTPServer

from optparse import OptionParser
from os.path import join as pjoin
sys.path.append(pjoin(os.path.dirname(__file__), '../'))

from yubico_client.yubico import BAD_STATUS_CODES
from yubico_client.py3 import b

mock_action = None
signature = None


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        global mock_action, signature

        if self.path.find('?') != -1:
            self.path, self.query_string = self.path.split('?', 1)
            split = self.query_string.split('&')
            self.query_string = dict([pair.split('=', 1) for pair in split])

        else:
            self.query_string = {}

        if self.path == '/set_mock_action':
            action = self.query_string['action']

            if 'signature' in self.query_string:
                signature = self.query_string['signature']
            else:
                signature = None

            print('Setting mock_action to %s' % (action))
            mock_action = action
            self._end(status_code=200)
            return

        if mock_action in BAD_STATUS_CODES:
            return self._send_status(status=mock_action)
        elif mock_action == 'no_such_client':
            return self._send_status(status='NO_SUCH_CLIENT')
        elif mock_action == 'no_signature_ok':
            return self._send_status(status='OK')
        elif mock_action == 'ok_signature':
            return self._send_status(status='OK',
                                     signature=signature)
        elif mock_action == 'no_signature_ok_invalid_otp_in_response':
            return self._send_status(status='OK',
                                     signature=signature, otp='different')
        elif mock_action == 'no_signature_ok_invalid_nonce_in_response':
            return self._send_status(status='OK',
                                     signature=signature, nonce='different')
        elif mock_action == 'timeout':
            time.sleep(1)
            return self._send_status(status='OK')
        else:
            self._end(status_code=500)
            return

    def _end(self, status_code=200, body=''):
        print('Sending response: status_code=%s, body=%s' %
              (status_code, body))
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(b(body))

    def _send_status(self, status, signature=None, otp=None, nonce=None):
        if signature:
            body = '\nh=%s\nstatus=%s' % (signature, status)
        else:
            body = 'status=%s' % (status)

        if otp:
            body += '&otp=%s' % (otp)

        if nonce:
            body += '&nonce=%s' % (nonce)

        self._end(body=b(body))


def main():
    usage = 'usage: %prog --port=<port>'
    parser = OptionParser(usage=usage)
    parser.add_option('--port', dest='port', default=8881,
                      help='Port to listen on', metavar='PORT')

    (options, args) = parser.parse_args()

    httpd = server_class(('127.0.0.1', int(options.port)), Handler)
    print('Mock API server listening on 127.0.0.1:%s' % (options.port))

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    httpd.server_close()


main()
