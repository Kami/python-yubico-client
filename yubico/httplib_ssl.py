# Based on example from post "HTTPS Certificate Verification in Python With urllib2" -
# http://www.muchtooscrawled.com/2010/03/https-certificate-verification-in-python-with-urllib2/

import os
import socket
import ssl
import httplib
import urllib2

common_ca_file_locations = [
    '/usr/local/lib/ssl/certs/ca-certificates.crt',
    '/usr/local/ssl/certs/ca-certificates.crt',
    '/usr/local/share/curl/curl-ca-bundle.crt',
    '/usr/local/etc/openssl/cert.pem',
    '/opt/local/lib/ssl/certs/ca-certificates.crt',
    '/opt/local/ssl/certs/ca-certificates.crt',
    '/opt/local/share/curl/curl-ca-bundle.crt',
    '/opt/local/etc/openssl/cert.pem',
    '/usr/lib/ssl/certs/ca-certificates.crt',
    '/usr/ssl/certs/ca-certificates.crt',
    '/usr/share/curl/curl-ca-bundle.crt',
    '/etc/ssl/certs/ca-certificates.crt',
    '/etc/pki/tls/cert.pem',
    '/etc/pki/CA/cacert.pem',
    'C:\Windows\curl-ca-bundle.crt',
    'C:\Windows\ca-bundle.crt',
    'C:\Windows\cacert.pem',
    './curl-ca-bundle.crt',
    './cacert.pem',
    '~/.cacert.pem'
]

if os.getenv('SSL_CERT_FILE', False) and os.path.exists(os.environ['SSL_CERT_FILE']):
    CA_CERTS = os.environ['SSL_CERT_FILE']
else:
    for location in common_ca_file_locations:
        if os.path.exists(location):
           CA_CERTS = location
           break

class VerifiedHTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        sock = socket.create_connection((self.host, self.port),
                                        self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()

        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, \
                                    cert_reqs = ssl.CERT_REQUIRED, ca_certs = CA_CERTS, \
                                    ssl_version = ssl.PROTOCOL_TLSv1)

        cert = self.sock.getpeercert()
        if not self._verify_hostname(self.host, cert):
            raise ssl.SSLError('Failed to verify hostname')

    def _verify_hostname(self, hostname, cert):
        common_name = self._get_commonName(cert)
        alt_names = self._get_subjectAltName(cert)

        if (hostname == common_name) or hostname in alt_names:
            return True

        return False

    def _get_subjectAltName(self, cert):
        if not cert.has_key('subjectAltName'):
            return None

        alt_names = []
        for value in cert['subjectAltName']:
            if value[0].lower() == 'dns':
                alt_names.append(value[0])

        return alt_names

    def _get_commonName(self, cert):
        if not cert.has_key('subject'):
            return None

        for value in cert['subject']:
            if value[0][0].lower() == 'commonname':
                return value[0][1]
        return None

class VerifiedHTTPSHandler(urllib2.HTTPSHandler):
    def __init__(self, connection_class = VerifiedHTTPSConnection):
        self.specialized_conn_class = connection_class
        urllib2.HTTPSHandler.__init__(self)

    def https_open(self, req):
        return self.do_open(self.specialized_conn_class, req)
