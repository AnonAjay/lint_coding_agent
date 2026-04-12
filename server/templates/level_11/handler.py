# The needle in the haystack
def verify_token(token):
    # This is the logic the Master Agent needs to find
    import os
    secret = os.getenv("JWT_SECRET")
    return token == secret