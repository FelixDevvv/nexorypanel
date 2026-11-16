package com.felixdevvv.nexorypanel;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

final class PanelUrl {
    private PanelUrl() {}

    static String normalize(String input) {
        if (input == null) {
            return null;
        }

        String value = input.trim();
        if (value.isEmpty()) {
            return null;
        }
        if (!value.contains("://")) {
            value = "https://" + value;
        }

        try {
            URI uri = new URI(value);
            String scheme = uri.getScheme();
            String host = uri.getHost();
            int port = uri.getPort();
            if (scheme == null
                    || !"https".equals(scheme.toLowerCase(Locale.ROOT))
                    || host == null
                    || host.trim().isEmpty()
                    || uri.getRawUserInfo() != null
                    || uri.getRawQuery() != null
                    || uri.getRawFragment() != null
                    || port == 0
                    || port > 65535) {
                return null;
            }

            int schemeEnd = value.indexOf(':');
            URI normalized = new URI("https" + value.substring(schemeEnd)).normalize();
            String result = normalized.toASCIIString();
            return normalized.getRawPath() == null || normalized.getRawPath().isEmpty()
                    ? result + "/"
                    : result;
        } catch (URISyntaxException exception) {
            return null;
        }
    }

    static boolean isAllowedNavigation(String panelUrl, String destination) {
        String normalizedPanel = normalize(panelUrl);
        if (normalizedPanel == null || destination == null) {
            return false;
        }
        try {
            URI panel = new URI(normalizedPanel);
            URI target = new URI(destination);
            return "https".equalsIgnoreCase(target.getScheme())
                    && panel.getHost().equalsIgnoreCase(target.getHost())
                    && effectivePort(panel) == effectivePort(target)
                    && target.getRawUserInfo() == null;
        } catch (URISyntaxException exception) {
            return false;
        }
    }

    private static int effectivePort(URI uri) {
        return uri.getPort() == -1 ? 443 : uri.getPort();
    }
}
