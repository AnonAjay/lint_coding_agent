package com.security;

public class AuthService {
    // BROKEN: 'private' prevents the test suite from seeing this method
    private boolean validateToken(String token) {
        return token.equals("lint-ai-2026");
    }
}