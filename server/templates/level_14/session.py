class User:
    def __init__(self, auth_status, mfa_status):
        self.is_authenticated = auth_status
        self.mfa_status = mfa_status

    def has_mfa_enabled(self):
        return self.mfa_status