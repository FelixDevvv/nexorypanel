package com.felixdevvv.nexorypanel;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class PanelUrlTest {
    @Test
    public void normalizesSecurePanelAddresses() {
        assertEquals("https://panel.example.com/", PanelUrl.normalize("panel.example.com"));
        assertEquals(
                "https://panel.example.com:8443/control",
                PanelUrl.normalize(" https://panel.example.com:8443/control "));
    }

    @Test
    public void rejectsInsecureOrCredentialBearingAddresses() {
        assertNull(PanelUrl.normalize("http://panel.example.com"));
        assertNull(PanelUrl.normalize("https://user:password@panel.example.com"));
        assertNull(PanelUrl.normalize("https://panel.example.com/?token=secret"));
        assertNull(PanelUrl.normalize("javascript:alert(1)"));
    }

    @Test
    public void allowsOnlyHttpsNavigationOnTheConfiguredOrigin() {
        assertTrue(PanelUrl.isAllowedNavigation(
                "https://panel.example.com/control",
                "https://panel.example.com/login"));
        assertTrue(PanelUrl.isAllowedNavigation(
                "https://panel.example.com",
                "https://panel.example.com:443/login"));
        assertTrue(PanelUrl.isAllowedNavigation(
                "https://panel.example.com:443",
                "https://panel.example.com/login"));
        assertFalse(PanelUrl.isAllowedNavigation(
                "https://panel.example.com",
                "https://another.example.com"));
        assertFalse(PanelUrl.isAllowedNavigation(
                "https://panel.example.com",
                "http://panel.example.com"));
        assertFalse(PanelUrl.isAllowedNavigation(
                "https://panel.example.com:8443",
                "https://panel.example.com"));
        assertFalse(PanelUrl.isAllowedNavigation(
                "https://panel.example.com",
                "https://user@panel.example.com"));
    }
}
