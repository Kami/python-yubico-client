"""
Class which holds data about an OTP.
"""

import modhex


class OTP(object):
    def __init__(self, otp, translate_otp=True):
        self.otp = self.get_otp_modehex_interpretation(otp) \
            if translate_otp else otp

        self.device_id = self.otp[:12]
        self.session_counter = None
        self.timestamp = None
        self.session_user = None

    def get_otp_modehex_interpretation(self, otp):
        # We only use the first interpretation, because
        # if the OTP uses all 16 characters in its alphabet
        # there is only one possible interpretation of that otp
        try:
            otp_translated = modhex.translate(unicode(otp)).pop()
        except Exception:
            otp_translated = otp

        return otp_translated

    def __repr__(self):
        return '%s, %s, %s' % (self.otp, self.device_id, self.timestamp)
