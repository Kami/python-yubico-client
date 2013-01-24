import sys
import unittest

import requests

from yubico import yubico
from yubico.otp import OTP
from yubico.yubico_exceptions import StatusCodeError, InvalidClientIdError
from yubico.yubico_exceptions import SignatureVerificationError
from yubico.yubico_exceptions import InvalidValidationResponse


class TestOTPClass(unittest.TestCase):
    def test_otp_class(self):
        otp1 = OTP('tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl')
        otp2 = OTP('jjjjjjjjnhe.ngcgjeiuujjjdtgihjuecyixinxunkhj',
                   translate_otp=True)

        self.assertEqual(otp1.device_id, 'tlerefhcvijl')
        self.assertEqual(otp2.otp,
                         'ccccccccljdeluiucdgffccchkugjcfditgbglbflvjc')


class TestYubicoVerifySingle(unittest.TestCase):
    def setUp(self):
        yubico.API_URLS = ('127.0.0.1:8881/wsapi/2.0/verify',)
        yubico.DEFAULT_TIMEOUT = 2
        yubico.CA_CERTS_BUNDLE_PATH = None

        self.client_no_verify_sig = yubico.Yubico('1234', None,
                                                  use_https=False)
        self.client_verify_sig = yubico.Yubico('1234', 'secret123456',
                                               use_https=False)

    def test_invalid_custom_ca_certs_path(self):
        if hasattr(sys, 'pypy_version_info'):
            # TODO: Figure out why this breaks PyPy
            return

        yubico.CA_CERTS_BUNDLE_PATH = '/does/not/exist.1'
        client = yubico.Yubico('1234', 'secret123456')

        try:
            client.verify('bad')
        except requests.exceptions.SSLError:
            pass
        else:
            self.fail('SSL exception was not thrown')

    def test_replayed_otp(self):
        self._set_mock_action('REPLAYED_OTP')

        try:
            self.client_no_verify_sig.verify('bad')
        except StatusCodeError, e:
            self.assertEqual(e.status_code, 'REPLAYED_OTP')

    def test_verify_bad_status_codes(self):
        for status in (set(yubico.BAD_STATUS_CODES) - set(['REPLAYED_OTP'])):
            self._set_mock_action(status)

            try:
                self.client_no_verify_sig.verify('bad')
            except Exception, e:
                self.assertEqual(str(e), 'NO_VALID_ANSWERS')

    def test_verify_local_timeout(self):
        self._set_mock_action('timeout')

        try:
            self.client_no_verify_sig.verify('bad')
        except Exception, e:
            self.assertEqual(str(e), 'NO_VALID_ANSWERS')

    def test_verify_invalid_signature(self):
        self._set_mock_action('no_signature_ok')

        try:
            self.client_verify_sig.verify('test')
        except SignatureVerificationError:
            pass
        else:
            self.fail('Exception was not thrown')

    def test_verify_no_such_client(self):
        self._set_mock_action('no_such_client')

        try:
            self.client_no_verify_sig.verify('test')
        except InvalidClientIdError, e:
            self.assertEqual(e.client_id, '1234')
        else:
            self.fail('Exception was not thrown')

    def test_verify_ok_dont_check_signature(self):
        self._set_mock_action('no_signature_ok')

        status = self.client_no_verify_sig.verify('test')
        self.assertTrue(status)

    def test_verify_ok_check_signature(self):
        signature = \
            self.client_verify_sig.generate_message_signature('status=OK')
        self._set_mock_action('ok_signature', signature=signature)

        status = self.client_verify_sig.verify('test')
        self.assertTrue(status)

    def test_verify_invalid_otp_returned_in_the_response(self):
        self._set_mock_action('no_signature_ok_invalid_otp_in_response')

        try:
            self.client_no_verify_sig.verify('test')
        except InvalidValidationResponse, e:
            self.assertTrue('Unexpected OTP in response' in e.message)
        else:
            self.fail('Exception was not thrown')

    def test_verify_invalid_nonce_returned_in_the_response(self):
        self._set_mock_action('no_signature_ok_invalid_nonce_in_response')

        try:
            self.client_no_verify_sig.verify('test')
        except InvalidValidationResponse, e:
            self.assertTrue('Unexpected nonce in response' in e.message)
        else:
            self.fail('Exception was not thrown')

    def _set_mock_action(self, action, port=8881, signature=None):
        path = '/set_mock_action?action=%s' % (action)

        if signature:
            path += '&signature=%s' % (signature)

        requests.get(url='http://127.0.0.1:%s%s' % (port, path))


if __name__ == '__main__':
    sys.exit(unittest.main())
