"""
Class which holds data about an OTP.
"""

class OTP():
	def __init__(self, otp):
		self.otp = otp
		
		self.device_id = otp[:12]
		self.session_counter = None
		self.timestamp = None
		self.session_user = None
		
	def __repr__(self):
		return '%s, %s, %s' % (self.otp, self.device_id, self.timestamp)