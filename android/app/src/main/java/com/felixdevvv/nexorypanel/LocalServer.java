package com.felixdevvv.nexorypanel;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.Locale;
import java.util.UUID;
import java.util.regex.Pattern;

final class LocalServer {
    static final String VANILLA = "vanilla";
    static final String PAPER = "paper";
    static final String PURPUR = "purpur";
    static final int DEFAULT_PORT = 25565;

    private static final Pattern ID_PATTERN = Pattern.compile("[a-f0-9]{32}");
    private static final Pattern VERSION_PATTERN =
            Pattern.compile("[0-9]+(?:\\.[0-9]+){1,3}(?:[-+][A-Za-z0-9._-]+)?");
    private static final Pattern BUILD_PATTERN = Pattern.compile("[A-Za-z0-9._-]{1,32}");

    final String id;
    final String name;
    final String software;
    final String version;
    final String build;
    final int ramMb;
    final int port;

    LocalServer(
            String id,
            String name,
            String software,
            String version,
            String build,
            int ramMb,
            int port) {
        if (!isValidId(id)) {
            throw new IllegalArgumentException("El identificador del servidor no es válido.");
        }
        String normalizedName = name == null ? "" : name.trim();
        if (normalizedName.isEmpty() || normalizedName.length() > 40
                || normalizedName.contains("\n") || normalizedName.contains("\r")) {
            throw new IllegalArgumentException("El nombre debe tener entre 1 y 40 caracteres.");
        }
        if (!isSupportedSoftware(software) || !isValidVersion(version)
                || !isValidBuild(build) || ramMb < 512 || ramMb > 16384
                || port < 1024 || port > 65535) {
            throw new IllegalArgumentException("La configuración del servidor no es válida.");
        }
        this.id = id;
        this.name = normalizedName;
        this.software = software.toLowerCase(Locale.ROOT);
        this.version = version;
        this.build = build;
        this.ramMb = ramMb;
        this.port = port;
    }

    static LocalServer create(
            String name,
            String software,
            String version,
            String build,
            int ramMb,
            int port) {
        return new LocalServer(
                UUID.randomUUID().toString().replace("-", ""),
                name,
                software,
                version,
                build,
                ramMb,
                port);
    }

    static boolean isSupportedSoftware(String software) {
        return VANILLA.equals(software) || PAPER.equals(software) || PURPUR.equals(software);
    }

    static boolean isValidId(String id) {
        return id != null && ID_PATTERN.matcher(id).matches();
    }

    static boolean isValidVersion(String version) {
        return version != null && VERSION_PATTERN.matcher(version).matches();
    }

    static boolean isValidBuild(String build) {
        return build != null && BUILD_PATTERN.matcher(build).matches();
    }

    String termuxSessionName() {
        return "nx_" + id;
    }

    JSONObject toJson() throws JSONException {
        JSONObject json = new JSONObject();
        json.put("id", id);
        json.put("name", name);
        json.put("software", software);
        json.put("version", version);
        json.put("build", build);
        json.put("ramMb", ramMb);
        json.put("port", port);
        return json;
    }

    static LocalServer fromJson(JSONObject json) {
        if (json == null) {
            return null;
        }
        try {
            return new LocalServer(
                    json.getString("id"),
                    json.getString("name"),
                    json.getString("software"),
                    json.getString("version"),
                    json.getString("build"),
                    json.getInt("ramMb"),
                    json.getInt("port"));
        } catch (JSONException | IllegalArgumentException exception) {
            return null;
        }
    }
}
