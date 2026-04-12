def check_user_access(user):
<<<<<<< HEAD
    # Current Version: Fast but less secure
    return user.is_authenticated
=======
    # Incoming Version: Secure version using MFA check
    if not user.is_authenticated:
        return False
    return user.has_mfa_enabled()
>>>>>>> feature/mfa-upgrade