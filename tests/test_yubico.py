import sys
import unittest

import requests

from yubico_client import yubico
from yubico_client.otp import OTP
from yubico_client.py3 import PY3, unittest2_required
from yubico_client.yubico_exceptions import StatusCodeError
from yubico_client.yubico_exceptions import InvalidClientIdError
from yubico_client.yubico_exceptions import SignatureVerificationError
from yubico_client.yubico_exceptions import InvalidValidationResponse

if unittest2_required:
    import unittest2 as unittest  # NOQA
else:
    import unittest

LOCAL_SERVER = ('127.0.0.1:8881/wsapi/2.0/verify',)


class TestOTPClass(unittest.TestCase):
    def test_otp_class(self):
        otp1 = OTP('tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl')
        otp2 = OTP('jjjjjjjjnhe.ngcgjeiuujjjdtgihjuecyixinxunkhj',
                   translate_otp=True)

        self.assertEqual(otp1.device_id, 'tlerefhcvijl')
        self.assertEqual(otp2.otp,
                         'ccccccccljdeluiucdgffccchkugjcfditgbglbflvjc')

    def test_translation_multiple_interpretations(self):
        otp_str1 = 'vvbtbtndhtlfguefgluvbdcetnitidgkvfkbicevgcin'
        otp1 = OTP(otp_str1)
        self.assertEqual(otp1.otp, otp_str1)

    def test_translation_single_interpretation(self):
        otp_str1 = 'cccfgvgitchndibrrtuhdrgeufrdkrjfgutfjbnhhglv'
        otp_str2 = 'cccagvgitchndibrrtuhdrgeufrdkrjfgutfjbnhhglv'
        otp1 = OTP(otp_str1)
        otp2 = OTP(otp_str2)
        self.assertEqual(otp1.otp, otp_str1)
        self.assertEqual(otp2.otp, otp_str2)


class TestYubicoVerifySingle(unittest.TestCase):
    def setUp(self):
        yubico.DEFAULT_TIMEOUT = 2
        yubico.CA_CERTS_BUNDLE_PATH = None

        self.client_no_verify_sig = yubico.Yubico('1234', None,
                                                  api_urls=LOCAL_SERVER,
                                                  use_https=False)
        self.client_verify_sig = yubico.Yubico('1234', 'secret123456',
                                               api_urls=LOCAL_SERVER,
                                               use_https=False)

    def test_invalid_custom_ca_certs_path(self):
        if hasattr(sys, 'pypy_version_info') or PY3:
            # TODO: Figure out why this breaks PyPy and 3.3
            return

        yubico.CA_CERTS_BUNDLE_PATH = '/does/not/exist.1'
        client = yubico.Yubico('1234', 'secret123456', api_urls=LOCAL_SERVER)

        try:
            client.verify('bad')
        except requests.exceptions.SSLError:
            pass
        else:
            self.fail('SSL exception was not thrown')
        finally:
            yubico.CA_CERTS_BUNDLE_PATH = None

    def test_replayed_otp(self):
        self._set_mock_action('REPLAYED_OTP')

        try:
            self.client_no_verify_sig.verify('bad')
        except StatusCodeError:
            e = sys.exc_info()[1]
            self.assertEqual(e.status_code, 'REPLAYED_OTP')

    def test_verify_bad_status_codes(self):
        for status in (set(yubico.BAD_STATUS_CODES) - set(['REPLAYED_OTP'])):
            self._set_mock_action(status)

            try:
                self.client_no_verify_sig.verify('bad')
            except Exception:
                e = sys.exc_info()[1]
                self.assertEqual(str(e), 'NO_VALID_ANSWERS')

    def test_verify_local_timeout(self):
        self._set_mock_action('timeout')

        try:
            self.client_no_verify_sig.verify('bad')
        except Exception:
            e = sys.exc_info()[1]
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
        except InvalidClientIdError:
            e = sys.exc_info()[1]
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
        except InvalidValidationResponse:
            e = sys.exc_info()[1]
            self.assertTrue('Unexpected OTP in response' in e.message)
        else:
            self.fail('Exception was not thrown')

    def test_verify_invalid_nonce_returned_in_the_response(self):
        self._set_mock_action('no_signature_ok_invalid_nonce_in_response')

        try:
            self.client_no_verify_sig.verify('test')
        except InvalidValidationResponse:
            e = sys.exc_info()[1]
            self.assertTrue('Unexpected nonce in response' in e.message)
        else:
            self.fail('Exception was not thrown')

    def test_verify_multi_different_device_ids(self):
        otp_list = [
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl',
            'blerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl',
        ]

        expected_msg = 'OTPs contain different device ids'

        self.assertRaisesRegexp(Exception, expected_msg,
                                self.client_no_verify_sig.verify_multi,
                                otp_list=otp_list)

    def test_verify_multi_single_otp(self):
        otp_list = [
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl'
        ]

        expected_msg = 'otp_list needs to contain at least two OTPs'

        self.assertRaisesRegexp(ValueError, expected_msg,
                                self.client_no_verify_sig.verify_multi,
                                otp_list=otp_list)

    def test_verify_multi_too_much_time_passed_between_otp_generations(self):
        otp_list = [
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl',
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbc',
        ]

        max_time_window = 7

        def mock_verify(*args, **kwargs):
            otp = args[0]

            response = {}

            if otp == 'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl':
                timestamp = 1383997754 * 8
            elif otp == 'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbc':
                timestamp = (1383997754 + max_time_window + 1) * 8
            else:
                raise Exception('Invalid OTP')

            response['timestamp'] = timestamp
            return response

        self.client_no_verify_sig.verify = mock_verify

        expected_msg = ('More then 7 seconds has passed between generating '
                        'the first and the last OTP')

        self.assertRaisesRegexp(Exception, expected_msg,
                                self.client_no_verify_sig.verify_multi,
                                otp_list=otp_list,
                                max_time_window=max_time_window)

    def test_verify_multi_first_otp_is_older_than_last(self):
        otp_list = [
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl',
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbc',
        ]

        max_time_window = 7

        def mock_verify(*args, **kwargs):
            otp = args[0]

            response = {}

            if otp == 'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl':
                timestamp = (1383997754 + max_time_window + 1) * 8
            elif otp == 'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbc':
                timestamp = 1383997754 * 8
            else:
                raise Exception('Invalid OTP')

            response['timestamp'] = timestamp
            return response

        self.client_no_verify_sig.verify = mock_verify

        expected_msg = ('delta is smaller than zero. First OTP appears '
                        'to be older than the last one')

        self.assertRaisesRegexp(Exception, expected_msg,
                                self.client_no_verify_sig.verify_multi,
                                otp_list=otp_list,
                                max_time_window=max_time_window)

    def test_verify_multi_success(self):
        otp_list = [
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl',
            'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbc',
        ]

        def mock_verify(*args, **kwargs):
            otp = args[0]

            response = {}

            if otp == 'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbl':
                timestamp = 1383997754 * 8
            elif otp == 'tlerefhcvijlngibueiiuhkeibbcbecehvjiklltnbbc':
                timestamp = (1383997754 + 2) * 8
            else:
                raise Exception('Invalid OTP')

            response['timestamp'] = timestamp
            return response

        self.client_no_verify_sig.verify = mock_verify

        status = self.client_no_verify_sig.verify_multi(otp_list=otp_list)
        self.assertTrue(status)

    def _set_mock_action(self, action, port=8881, signature=None):
        path = '/set_mock_action?action=%s' % (action)

        if signature:
            path += '&signature=%s' % (signature)

        requests.get(url='http://127.0.0.1:%s%s' % (port, path))


class TestAPIUrls(unittest.TestCase):
    def test_default_urls_https(self):
        client = yubico.Yubico('1234', 'secret123456')
        https_urls = list(map(lambda url: 'https://' + url,
                              yubico.DEFAULT_API_URLS))
        self.assertEqual(client.api_urls, https_urls)

    def test_default_urls_http(self):
        client = yubico.Yubico('1234', 'secret123456', use_https=False)
        http_urls = list(map(lambda url: 'http://' + url,
                             yubico.DEFAULT_API_URLS))
        self.assertEqual(client.api_urls, http_urls)

    def test_custom_urls(self):
        custom_urls = ['https://example.com/wsapi/2.0/verify',
                       'http://example.com/wsapi/2.0/verify',
                       'example.com/wsapi/2.0/verify']
        verify_urls = custom_urls[:]
        verify_urls[2] = 'https://' + verify_urls[2]

        client = yubico.Yubico('1234', 'secret123456', api_urls=custom_urls)
        self.assertEqual(client.api_urls, verify_urls)

    def test_single_url(self):
        single_url = 'http://www.example.com'
        client = yubico.Yubico('1234', 'secret123456', api_urls=single_url)
        self.assertEqual(client.api_urls, [single_url])


if __name__ == '__main__':
    sys.exit(unittest.main())
