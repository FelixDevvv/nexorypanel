package com.felixdevvv.nexorypanel;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

final class MinecraftCatalog {
    private static final String USER_AGENT =
            "NexoryPanel/2.0.3 (+https://github.com/FelixDevvv/nexorypanel)";
    private static final String VANILLA_MANIFEST =
            "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json";
    private static final int MAX_RESPONSE_BYTES = 8 * 1024 * 1024;

    static final class Build {
        final String id;
        final String downloadUrl;
        final String checksumAlgorithm;
        final String checksum;

        Build(String id, String downloadUrl, String checksumAlgorithm, String checksum) {
            this.id = id;
            this.downloadUrl = downloadUrl;
            this.checksumAlgorithm = checksumAlgorithm;
            this.checksum = checksum;
        }
    }

    private MinecraftCatalog() {}

    static List<String> versions(String software) throws IOException, JSONException {
        requireSoftware(software);
        JSONObject response;
        Set<String> result = new LinkedHashSet<>();
        if (LocalServer.VANILLA.equals(software)) {
            response = requestJson(VANILLA_MANIFEST);
            JSONArray versions = response.optJSONArray("versions");
            if (versions == null) {
                throw new IOException("El manifiesto oficial de Minecraft no contiene versiones.");
            }
            for (int index = 0; index < versions.length(); index++) {
                JSONObject entry = versions.optJSONObject(index);
                if (entry != null && "release".equals(entry.optString("type"))) {
                    addVersion(result, entry.optString("id"));
                }
            }
        } else if (LocalServer.PAPER.equals(software)) {
            response = requestJson("https://fill.papermc.io/v3/projects/paper/versions");
            JSONArray versions = response.optJSONArray("versions");
            if (versions == null) {
                throw new IOException("PaperMC no devolvió una lista de versiones.");
            }
            for (int index = 0; index < versions.length(); index++) {
                JSONObject entry = versions.optJSONObject(index);
                JSONObject nested = entry == null ? null : entry.optJSONObject("version");
                addVersion(result, nested == null
                        ? entry == null ? "" : entry.optString("version")
                        : nested.optString("id"));
            }
        } else {
            response = requestJson("https://api.purpurmc.org/v2/purpur");
            JSONArray versions = response.optJSONArray("versions");
            if (versions == null) {
                throw new IOException("PurpurMC no devolvió una lista de versiones.");
            }
            for (int index = 0; index < versions.length(); index++) {
                addVersion(result, versions.optString(index));
            }
        }
        return new ArrayList<>(result);
    }

    static List<Build> builds(String software, String version) throws IOException, JSONException {
        requireSoftware(software);
        if (!LocalServer.isValidVersion(version)) {
            throw new IllegalArgumentException("La versión seleccionada no es válida.");
        }
        if (LocalServer.VANILLA.equals(software)) {
            JSONObject manifest = requestJson(VANILLA_MANIFEST);
            JSONArray versions = manifest.optJSONArray("versions");
            JSONObject selected = findVanillaVersion(versions, version);
            if (selected == null) {
                throw new IOException("No se encontró la versión Vanilla seleccionada.");
            }
            JSONObject metadata = requestJson(selected.getString("url"));
            JSONObject downloads = metadata.optJSONObject("downloads");
            JSONObject server = downloads == null ? null : downloads.optJSONObject("server");
            if (server == null) {
                throw new IOException("Esta versión no ofrece un JAR oficial de servidor.");
            }
            String url = server.optString("url");
            requireDownloadUrl(LocalServer.VANILLA, url);
            return Collections.singletonList(new Build(
                    "release",
                    url,
                    "sha1",
                    server.optString("sha1")));
        }
        if (LocalServer.PURPUR.equals(software)) {
            JSONObject response = requestJson("https://api.purpurmc.org/v2/purpur/"
                    + encodePath(version));
            JSONObject builds = response.optJSONObject("builds");
            JSONArray values = builds == null ? null : builds.optJSONArray("all");
            if (values == null || values.length() == 0) {
                throw new IOException("PurpurMC no devolvió builds para esa versión.");
            }
            List<Build> result = new ArrayList<>();
            for (int index = values.length() - 1; index >= 0; index--) {
                String id = values.optString(index);
                if (LocalServer.isValidBuild(id)) {
                    result.add(new Build(id,
                            "https://api.purpurmc.org/v2/purpur/" + encodePath(version)
                                    + "/" + encodePath(id) + "/download",
                            "", ""));
                }
            }
            return result;
        }

        JSONArray builds = requestJsonArray(
                "https://fill.papermc.io/v3/projects/paper/versions/"
                        + encodePath(version) + "/builds");
        if (builds.length() == 0) {
            throw new IOException("PaperMC no devolvió builds para esa versión.");
        }
        List<Build> result = new ArrayList<>();
        for (int index = builds.length() - 1; index >= 0; index--) {
            JSONObject entry = builds.optJSONObject(index);
            if (entry == null) {
                continue;
            }
            String id = entry.optString("id");
            JSONObject downloads = entry.optJSONObject("downloads");
            JSONObject server = downloads == null ? null : downloads.optJSONObject("server:default");
            if (server == null && downloads != null) {
                server = downloads.optJSONObject("server");
            }
            if (!LocalServer.isValidBuild(id) || server == null) {
                continue;
            }
            String url = server.optString("url");
            requireDownloadUrl(LocalServer.PAPER, url);
            JSONObject checksums = server.optJSONObject("checksums");
            String sha256 = checksums == null ? "" : checksums.optString("sha256");
            result.add(new Build(id, url, sha256.isEmpty() ? "" : "sha256", sha256));
        }
        if (result.isEmpty()) {
            throw new IOException("PaperMC no devolvió descargas válidas para esa versión.");
        }
        return result;
    }

    static void requireDownloadUrl(String software, String value) throws IOException {
        try {
            URI uri = URI.create(value);
            String host = uri.getHost();
            boolean allowed = "https".equalsIgnoreCase(uri.getScheme())
                    && host != null
                    && ((LocalServer.VANILLA.equals(software) && "piston-data.mojang.com".equalsIgnoreCase(host))
                    || (LocalServer.PAPER.equals(software) && "fill-data.papermc.io".equalsIgnoreCase(host))
                    || (LocalServer.PURPUR.equals(software) && "api.purpurmc.org".equalsIgnoreCase(host)));
            if (!allowed) {
                throw new IOException("El enlace de descarga no pertenece al servidor oficial esperado.");
            }
        } catch (IllegalArgumentException exception) {
            throw new IOException("El enlace de descarga oficial no es válido.", exception);
        }
    }

    private static JSONObject requestJson(String address) throws IOException, JSONException {
        return new JSONObject(requestText(address));
    }

    private static JSONArray requestJsonArray(String address) throws IOException, JSONException {
        return new JSONArray(requestText(address));
    }

    private static String requestText(String address) throws IOException {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(address).openConnection();
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(20000);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("User-Agent", USER_AGENT);
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) {
                throw new IOException("La fuente oficial respondió HTTP " + status + ".");
            }
            try (InputStream input = connection.getInputStream();
                 ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                byte[] buffer = new byte[8192];
                int total = 0;
                int count;
                while ((count = input.read(buffer)) != -1) {
                    total += count;
                    if (total > MAX_RESPONSE_BYTES) {
                        throw new IOException("La respuesta de versiones supera el tamaño permitido.");
                    }
                    output.write(buffer, 0, count);
                }
                return new String(output.toByteArray(), StandardCharsets.UTF_8);
            }
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static JSONObject findVanillaVersion(JSONArray versions, String version)
            throws IOException {
        if (versions == null) {
            throw new IOException("El manifiesto oficial de Minecraft no contiene versiones.");
        }
        for (int index = 0; index < versions.length(); index++) {
            JSONObject entry = versions.optJSONObject(index);
            if (entry != null && version.equals(entry.optString("id"))
                    && "release".equals(entry.optString("type"))) {
                return entry;
            }
        }
        return null;
    }

    private static String encodePath(String value) {
        return value.replace("%", "%25").replace("/", "%2F").replace(" ", "%20");
    }

    private static void addVersion(Set<String> versions, String version) {
        if (LocalServer.isValidVersion(version)) {
            versions.add(version);
        }
    }

    private static void requireSoftware(String software) {
        if (!LocalServer.isSupportedSoftware(software)) {
            throw new IllegalArgumentException("Software no admitido.");
        }
    }
}
