package com.tests;
import com.security.AuthService;

public class SecurityTest {
    public void testLogin() {
        AuthService auth = new AuthService();
        // This line causes a "method has private access" compiler error
        if (auth.validateToken("lint-ai-2026")) {
            System.out.println("Test Passed");
        }
    }
}