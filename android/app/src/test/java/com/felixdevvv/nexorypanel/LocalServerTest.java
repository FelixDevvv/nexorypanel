package com.felixdevvv.nexorypanel;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class LocalServerTest {
    @Test
    public void createsSafeTermuxSessionNames() {
        LocalServer server = LocalServer.create(
                "Mi servidor",
                LocalServer.PAPER,
                "1.21.11",
                "42",
                2048,
                25565);

        assertTrue(LocalServer.isValidId(server.id));
        assertEquals("nx_" + server.id, server.termuxSessionName());
        assertEquals("Mi servidor", server.name);
        assertEquals(25565, server.port);
    }

    @Test
    public void acceptsOnlySupportedSoftwareAndSafeReleaseValues() {
        assertTrue(LocalServer.isSupportedSoftware(LocalServer.VANILLA));
        assertTrue(LocalServer.isSupportedSoftware(LocalServer.PAPER));
        assertTrue(LocalServer.isSupportedSoftware(LocalServer.PURPUR));
        assertFalse(LocalServer.isSupportedSoftware("forge"));
        assertFalse(LocalServer.isValidVersion("../server"));
        assertFalse(LocalServer.isValidBuild("1; rm -rf"));
    }

    @Test(expected = IllegalArgumentException.class)
    public void rejectsOutOfRangeMemory() {
        LocalServer.create("Test", LocalServer.VANILLA, "1.21.11", "release", 128, 25565);
    }

    @Test(expected = IllegalArgumentException.class)
    public void rejectsInvalidServerIdentifiers() {
        new LocalServer("../outside", "Test", LocalServer.VANILLA, "1.21.11", "release", 1024, 25565);
    }
}
