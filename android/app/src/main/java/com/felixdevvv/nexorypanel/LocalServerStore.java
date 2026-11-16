package com.felixdevvv.nexorypanel;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

final class LocalServerStore {
    private static final String PREFERENCES = "nexory-local-servers";
    private static final String SERVERS_KEY = "servers";

    private final SharedPreferences preferences;

    LocalServerStore(Context context) {
        preferences = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE);
    }

    List<LocalServer> load() {
        List<LocalServer> servers = new ArrayList<>();
        String raw = preferences.getString(SERVERS_KEY, "[]");
        try {
            JSONArray entries = new JSONArray(raw);
            for (int index = 0; index < entries.length(); index++) {
                LocalServer server = LocalServer.fromJson(entries.optJSONObject(index));
                if (server != null) {
                    servers.add(server);
                }
            }
        } catch (JSONException exception) {
            throw new IllegalStateException("No se pudo leer la lista local de servidores.", exception);
        }
        return servers;
    }

    void save(List<LocalServer> servers) {
        JSONArray entries = new JSONArray();
        try {
            for (LocalServer server : servers) {
                entries.put(server.toJson());
            }
        } catch (JSONException exception) {
            throw new IllegalStateException("No se pudo guardar la lista local de servidores.", exception);
        }
        if (!preferences.edit().putString(SERVERS_KEY, entries.toString()).commit()) {
            throw new IllegalStateException("Android no pudo guardar la lista local de servidores.");
        }
    }
}
