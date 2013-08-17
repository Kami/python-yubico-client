from yubico_client.modhex import translate
from yubico_client.py3 import u


class OTP(object):
    """
    Class which holds data about an OTP.
    """

    def __init__(self, otp, translate_otp=True):
        """
        Represents an OTP token.

        :param otp: OTP token.
        :type: otp: ``str``

        :param translate_otp: True if the OTP should be translated.
        :type translate_otp: ``bool``
        """
        if translate_otp:
            self.otp = self.get_otp_modehex_interpretation(otp)
        else:
            self.otp = otp

        self.device_id = self.otp[:12]
        self.session_counter = None
        self.timestamp = None
        self.session_user = None

    def get_otp_modehex_interpretation(self, otp):
        """
        Return modhex interpretation of the provided OTP.

        If there are multiple interpretations available, first one is used,
        because if the OTP uses all 16 characters in its alphabet there is only
        one possible interpretation of that OTP.

        :return: Modhex interpretation of the OTP.
        :rtype: ``str``
        """
        try:
            interpretations = translate(u(otp))
        except Exception:
            return otp

        if len(interpretations) == 0:
            return otp
        elif len(interpretations) > 1:
            # If there are multiple interpretations first try to use the same
            # translation as the input OTP. If the one is not found, use the
            # random interpretation.
            if u(otp) in interpretations:
                return otp

        return interpretations.pop()

    def __repr__(self):
        return '%s, %s, %s' % (self.otp, self.device_id, self.timestamp)
