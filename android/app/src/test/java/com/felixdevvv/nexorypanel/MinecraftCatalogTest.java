package com.felixdevvv.nexorypanel;

import static org.junit.Assert.assertThrows;

import org.junit.Test;

import java.io.IOException;

public class MinecraftCatalogTest {
    @Test
    public void acceptsOnlyHttpsDownloadsFromExpectedOfficialHosts() throws IOException {
        MinecraftCatalog.requireDownloadUrl(
                LocalServer.VANILLA,
                "https://piston-data.mojang.com/v1/objects/example/server.jar");
        MinecraftCatalog.requireDownloadUrl(
                LocalServer.PAPER,
                "https://fill-data.papermc.io/file/example/server.jar");
        MinecraftCatalog.requireDownloadUrl(
                LocalServer.PURPUR,
                "https://api.purpurmc.org/v2/purpur/1.21.11/1/download");
    }

    @Test
    public void rejectsUntrustedAndInsecureDownloadUrls() {
        assertThrows(IOException.class, () -> MinecraftCatalog.requireDownloadUrl(
                LocalServer.PAPER,
                "https://example.com/server.jar"));
        assertThrows(IOException.class, () -> MinecraftCatalog.requireDownloadUrl(
                LocalServer.VANILLA,
                "http://piston-data.mojang.com/server.jar"));
        assertThrows(IOException.class, () -> MinecraftCatalog.requireDownloadUrl(
                LocalServer.PURPUR,
                "https://api.purpurmc.org.evil.example/server.jar"));
    }
}
