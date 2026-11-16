package com.felixdevvv.nexorypanel;

import android.app.Activity;
import android.app.ActivityManager;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

public final class MainActivity extends Activity {
    private static final int BACKGROUND = Color.rgb(16, 13, 27);
    private static final int SURFACE = Color.rgb(29, 24, 45);
    private static final int SURFACE_ALT = Color.rgb(39, 31, 58);
    private static final int PRIMARY = Color.rgb(168, 85, 247);
    private static final int TEXT = Color.rgb(248, 245, 255);
    private static final int MUTED = Color.rgb(183, 174, 202);
    private static final int SUCCESS = Color.rgb(118, 228, 176);
    private static final int ERROR = Color.rgb(255, 139, 151);

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final AtomicInteger versionRequests = new AtomicInteger();
    private final AtomicInteger buildRequests = new AtomicInteger();
    private LocalServerStore serverStore;
    private List<LocalServer> servers;
    private LinearLayout homeContent;
    private boolean hasResumed;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(BACKGROUND);
        window.setNavigationBarColor(BACKGROUND);
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        serverStore = new LocalServerStore(this);
        servers = serverStore.load();
        showHome();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (hasResumed) {
            showHome();
        }
        hasResumed = true;
    }

    @Override
    protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }

    private void showHome() {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(BACKGROUND);

        homeContent = new LinearLayout(this);
        homeContent.setOrientation(LinearLayout.VERTICAL);
        homeContent.setPadding(dp(20), dp(28), dp(20), dp(28));

        TextView eyebrow = text("NEXORY • ANDROID", 12, PRIMARY, true);
        eyebrow.setLetterSpacing(0.12f);
        homeContent.addView(eyebrow, matchWrap());

        TextView title = text("Tus servidores,\nen tu teléfono.", 30, TEXT, true);
        title.setLineSpacing(dp(2), 1f);
        LinearLayout.LayoutParams titleParams = matchWrap();
        titleParams.topMargin = dp(8);
        homeContent.addView(title, titleParams);

        TextView subtitle = text(
                "Minecraft Java Vanilla, Paper y Purpur ejecutándose localmente mediante Termux.",
                14,
                MUTED,
                false);
        subtitle.setLineSpacing(dp(4), 1f);
        LinearLayout.LayoutParams subtitleParams = matchWrap();
        subtitleParams.topMargin = dp(10);
        subtitleParams.bottomMargin = dp(22);
        homeContent.addView(subtitle, subtitleParams);

        addTermuxSetupCard();
        addSectionTitle("Mis servidores");

        if (servers.isEmpty()) {
            TextView empty = text(
                    "Todavía no tienes servidores. Configura Termux y crea uno para descargarlo en el teléfono.",
                    14,
                    MUTED,
                    false);
            empty.setPadding(dp(14), dp(16), dp(14), dp(16));
            empty.setBackground(rounded(SURFACE, dp(14), SURFACE));
            LinearLayout.LayoutParams emptyParams = matchWrap();
            emptyParams.topMargin = dp(8);
            homeContent.addView(empty, emptyParams);
        } else {
            for (LocalServer server : new ArrayList<>(servers)) {
                addServerCard(server);
            }
        }

        Button create = button("＋  Crear servidor");
        LinearLayout.LayoutParams createParams = matchWrap();
        createParams.topMargin = dp(20);
        homeContent.addView(create, createParams);
        create.setOnClickListener(view -> showCreateServerDialog());

        TextView note = text(
                "El servidor corre en Termux. Mantén Termux instalado y evita forzar su detención mientras juegas.",
                12,
                MUTED,
                false);
        note.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams noteParams = matchWrap();
        noteParams.topMargin = dp(18);
        homeContent.addView(note, noteParams);

        scroll.addView(homeContent);
        setContentView(scroll);
    }

    private void addTermuxSetupCard() {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(15), dp(16), dp(16));
        card.setBackground(rounded(SURFACE, dp(16), SURFACE));

        boolean installed = TermuxCommandClient.isInstalled(this);
        TextView heading = text(
                installed ? "Motor Android: Termux" : "Configura el motor de servidores",
                16,
                TEXT,
                true);
        card.addView(heading, matchWrap());
        TextView details = text(
                installed
                        ? "Necesitas Termux 0.109 o posterior, permiso para comandos externos y Java 25."
                        : "Instala Termux desde F-Droid o su GitHub oficial. Nexory no incluye una JVM en el APK.",
                13,
                MUTED,
                false);
        details.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams detailsParams = matchWrap();
        detailsParams.topMargin = dp(7);
        detailsParams.bottomMargin = dp(12);
        card.addView(details, detailsParams);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        if (installed) {
            Button setup = secondaryButton("Permisos e instrucciones");
            actions.addView(setup, new LinearLayout.LayoutParams(0, dp(46), 1f));
            setup.setOnClickListener(view -> showTermuxInstructions());

            Button installRuntime = button("Instalar Java");
            LinearLayout.LayoutParams runtimeParams = new LinearLayout.LayoutParams(0, dp(46), 1f);
            runtimeParams.leftMargin = dp(8);
            actions.addView(installRuntime, runtimeParams);
            installRuntime.setOnClickListener(view -> installTermuxPackages());
        } else {
            Button install = button("Descargar Termux");
            actions.addView(install, new LinearLayout.LayoutParams(0, dp(46), 1f));
            install.setOnClickListener(view -> openTermuxDownload());
        }
        card.addView(actions);

        LinearLayout.LayoutParams cardParams = matchWrap();
        cardParams.bottomMargin = dp(22);
        homeContent.addView(card, cardParams);
    }

    private void addSectionTitle(String title) {
        TextView heading = text(title, 18, TEXT, true);
        LinearLayout.LayoutParams params = matchWrap();
        params.bottomMargin = dp(4);
        homeContent.addView(heading, params);
    }

    private void addServerCard(LocalServer server) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(15), dp(14), dp(15), dp(14));
        card.setBackground(rounded(SURFACE, dp(15), SURFACE));

        LinearLayout headingRow = new LinearLayout(this);
        headingRow.setGravity(Gravity.CENTER_VERTICAL);
        TextView title = text(server.name, 17, TEXT, true);
        headingRow.addView(title, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        TextView softwareBadge = text(softwareName(server.software), 11, PRIMARY, true);
        softwareBadge.setPadding(dp(9), dp(5), dp(9), dp(5));
        softwareBadge.setBackground(rounded(SURFACE_ALT, dp(20), SURFACE_ALT));
        headingRow.addView(softwareBadge);
        card.addView(headingRow);

        TextView description = text(
                "Minecraft " + server.version + " • Build " + server.build + " • "
                        + server.ramMb + " MB heap • Puerto " + server.port,
                12,
                MUTED,
                false);
        LinearLayout.LayoutParams descriptionParams = matchWrap();
        descriptionParams.topMargin = dp(7);
        card.addView(description, descriptionParams);

        TextView state = text("Comprobando estado…", 12, MUTED, false);
        LinearLayout.LayoutParams stateParams = matchWrap();
        stateParams.topMargin = dp(9);
        card.addView(state, stateParams);

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams actionsParams = matchWrap();
        actionsParams.topMargin = dp(11);
        card.addView(actions, actionsParams);

        boolean[] running = {false};
        Button startStop = button("Iniciar");
        actions.addView(startStop, new LinearLayout.LayoutParams(0, dp(44), 1f));
        startStop.setOnClickListener(view -> {
            startStop.setEnabled(false);
            if (running[0]) {
                stopServer(server, result -> {
                    startStop.setEnabled(true);
                    if (!result.succeeded()) {
                        showError(result.describeFailure());
                    } else {
                        showToast("Se envió el comando de apagado.");
                    }
                    mainHandler.postDelayed(
                            () -> refreshOneServer(server, running, state, startStop),
                            1800);
                });
            } else {
                startServer(server, result -> {
                    startStop.setEnabled(true);
                    if (!result.succeeded()) {
                        showError(result.describeFailure());
                    } else {
                        showToast("Servidor iniciado en Termux.");
                    }
                    refreshOneServer(server, running, state, startStop);
                });
            }
        });

        Button console = secondaryButton("Consola");
        LinearLayout.LayoutParams consoleParams = new LinearLayout.LayoutParams(0, dp(44), 1f);
        consoleParams.leftMargin = dp(8);
        actions.addView(console, consoleParams);
        console.setOnClickListener(view -> showConsole(server));

        Button delete = secondaryButton("Eliminar");
        LinearLayout.LayoutParams deleteParams = new LinearLayout.LayoutParams(0, dp(44), 1f);
        deleteParams.leftMargin = dp(8);
        actions.addView(delete, deleteParams);
        delete.setOnClickListener(view -> confirmDeleteServer(server));

        LinearLayout.LayoutParams cardParams = matchWrap();
        cardParams.topMargin = dp(9);
        homeContent.addView(card, cardParams);
        refreshOneServer(server, running, state, startStop);
    }

    private void refreshOneServer(
            LocalServer server,
            boolean[] running,
            TextView state,
            Button startStop) {
        if (!TermuxCommandClient.isInstalled(this)) {
            running[0] = false;
            state.setText("Instala Termux para controlar este servidor.");
            state.setTextColor(ERROR);
            startStop.setText("Iniciar");
            return;
        }
        runTermuxScript("tmux has-session -t " + shellQuote(server.termuxSessionName())
                        + " 2>/dev/null",
                result -> {
                    running[0] = result.exitCode == 0 && result.internalError == -1;
                    state.setText(running[0] ? "●  En ejecución" : "○  Detenido");
                    state.setTextColor(running[0] ? SUCCESS : MUTED);
                    startStop.setText(running[0] ? "Detener" : "Iniciar");
                });
    }

    private void showCreateServerDialog() {
        if (!TermuxCommandClient.isInstalled(this)) {
            showTermuxInstructions();
            return;
        }

        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(18), dp(8), dp(18), dp(4));

        EditText name = field("Nombre del servidor", InputType.TYPE_CLASS_TEXT);
        name.setText("Mi servidor");
        content.addView(name, matchWrap());

        Spinner software = spinner();
        ArrayAdapter<String> softwareAdapter = adapter(
                new String[]{"Minecraft Vanilla", "PaperMC", "PurpurMC"});
        software.setAdapter(softwareAdapter);
        LinearLayout.LayoutParams softwareParams = matchWrap();
        softwareParams.topMargin = dp(12);
        content.addView(software, softwareParams);

        TextView versionLabel = text("Versión", 13, MUTED, true);
        LinearLayout.LayoutParams labelParams = matchWrap();
        labelParams.topMargin = dp(14);
        content.addView(versionLabel, labelParams);
        Spinner versions = spinner();
        versions.setAdapter(adapter(new String[]{"Cargando versiones…"}));
        LinearLayout.LayoutParams versionParams = matchWrap();
        versionParams.topMargin = dp(5);
        content.addView(versions, versionParams);

        TextView buildLabel = text("Build", 13, MUTED, true);
        LinearLayout.LayoutParams buildLabelParams = matchWrap();
        buildLabelParams.topMargin = dp(14);
        content.addView(buildLabel, buildLabelParams);
        Spinner builds = spinner();
        builds.setAdapter(adapter(new String[]{"Selecciona una versión"}));
        LinearLayout.LayoutParams buildParams = matchWrap();
        buildParams.topMargin = dp(5);
        content.addView(builds, buildParams);

        EditText ram = field("Memoria máxima de Java (MB)", InputType.TYPE_CLASS_NUMBER);
        ram.setText(String.valueOf(Math.min(2048, maximumServerHeapMb())));
        LinearLayout.LayoutParams ramParams = matchWrap();
        ramParams.topMargin = dp(14);
        content.addView(ram, ramParams);

        EditText port = field("Puerto (TCP)", InputType.TYPE_CLASS_NUMBER);
        port.setText(String.valueOf(nextAvailablePort()));
        LinearLayout.LayoutParams portParams = matchWrap();
        portParams.topMargin = dp(12);
        content.addView(port, portParams);

        CheckBox eula = new CheckBox(this);
        eula.setText("Acepto el EULA de Minecraft para este servidor.");
        eula.setTextColor(TEXT);
        eula.setButtonTintList(android.content.res.ColorStateList.valueOf(PRIMARY));
        LinearLayout.LayoutParams eulaParams = matchWrap();
        eulaParams.topMargin = dp(10);
        content.addView(eula, eulaParams);

        TextView eulaLink = text("El servidor descargado queda dentro del espacio privado de Termux.", 12, MUTED, false);
        content.addView(eulaLink, matchWrap());

        ScrollView formScroll = new ScrollView(this);
        formScroll.setFillViewport(true);
        formScroll.addView(content);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Crear servidor local")
                .setView(formScroll)
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Descargar e instalar", null)
                .create();

        List<MinecraftCatalog.Build> selectedBuilds = new ArrayList<>();
        software.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                loadVersions(softwareKey(position), versions, builds, selectedBuilds, buildLabel);
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });
        versions.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                String key = softwareKey(software.getSelectedItemPosition());
                Object selected = versions.getSelectedItem();
                if (selected != null && LocalServer.isValidVersion(selected.toString())) {
                    loadBuilds(key, selected.toString(), builds, selectedBuilds, buildLabel);
                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        dialog.setOnShowListener(ignored -> {
            Button install = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
            install.setOnClickListener(view -> {
                String serverName = name.getText().toString().trim();
                String softwareKey = softwareKey(software.getSelectedItemPosition());
                Object versionValue = versions.getSelectedItem();
                int buildPosition = builds.getSelectedItemPosition();
                int ramMb;
                int portNumber;
                try {
                    ramMb = Integer.parseInt(ram.getText().toString().trim());
                    portNumber = Integer.parseInt(port.getText().toString().trim());
                } catch (NumberFormatException exception) {
                    showError("Escribe cantidades válidas de memoria y puerto.");
                    return;
                }
                if (!eula.isChecked()) {
                    showError("Confirma el EULA antes de instalar el servidor.");
                    return;
                }
                if (versionValue == null || !LocalServer.isValidVersion(versionValue.toString())
                        || buildPosition < 0 || buildPosition >= selectedBuilds.size()) {
                    showError("Espera a que se carguen versiones y builds válidas.");
                    return;
                }
                if (serverName.isEmpty() || serverName.length() > 40
                        || ramMb < 512 || ramMb > maximumServerHeapMb()
                        || portNumber < 1024 || portNumber > 65535) {
                    showError("Usa un nombre de hasta 40 caracteres, una RAM entre 512 MB y "
                            + maximumServerHeapMb() + " MB, y un puerto entre 1024 y 65535.");
                    return;
                }
                if (isPortInUse(portNumber)) {
                    showError("Ese puerto ya está asignado a otro servidor.");
                    return;
                }
                int assignedRam = 0;
                for (LocalServer existing : servers) {
                    assignedRam += existing.ramMb;
                }
                if (assignedRam + ramMb > maximumServerHeapMb()) {
                    showError("El total de memoria asignada no puede superar "
                            + maximumServerHeapMb() + " MB en este teléfono.");
                    return;
                }

                LocalServer server;
                try {
                    MinecraftCatalog.Build selected = selectedBuilds.get(buildPosition);
                    server = LocalServer.create(
                            serverName,
                            softwareKey,
                            versionValue.toString(),
                            selected.id,
                            ramMb,
                            portNumber);
                    MinecraftCatalog.requireDownloadUrl(softwareKey, selected.downloadUrl);
                } catch (IllegalArgumentException | IOException exception) {
                    showError(exception.getMessage());
                    return;
                }
                install.setEnabled(false);
                install.setText("Descargando…");
                installServer(server, selectedBuilds.get(buildPosition), result -> {
                    install.setEnabled(true);
                    install.setText("Descargar e instalar");
                    if (!result.succeeded()) {
                        showError(result.describeFailure());
                        return;
                    }
                    servers.add(server);
                    try {
                        serverStore.save(servers);
                    } catch (IllegalStateException exception) {
                        servers.remove(server);
                        showError(exception.getMessage());
                        return;
                    }
                    dialog.dismiss();
                    showHome();
                    showToast("Servidor instalado en Termux.");
                });
            });
        });
        dialog.show();
        loadVersions(softwareKey(0), versions, builds, selectedBuilds, buildLabel);
    }

    private void loadVersions(
            String software,
            Spinner versionSpinner,
            Spinner buildSpinner,
            List<MinecraftCatalog.Build> selectedBuilds,
            TextView buildLabel) {
        int request = versionRequests.incrementAndGet();
        buildRequests.incrementAndGet();
        ArrayAdapter<String> loading = adapter(new String[]{"Cargando versiones…"});
        versionSpinner.setAdapter(loading);
        buildSpinner.setAdapter(adapter(new String[]{"Esperando versión…"}));
        selectedBuilds.clear();
        buildLabel.setText("Build");
        io.execute(() -> {
            try {
                List<String> values = MinecraftCatalog.versions(software);
                mainHandler.post(() -> {
                    if (request != versionRequests.get() || isFinishing()) {
                        return;
                    }
                    versionSpinner.setAdapter(adapter(values.toArray(new String[0])));
                    if (values.isEmpty()) {
                        buildSpinner.setAdapter(adapter(new String[]{"Sin builds disponibles"}));
                    }
                });
            } catch (Exception exception) {
                mainHandler.post(() -> {
                    if (request == versionRequests.get()) {
                        versionSpinner.setAdapter(adapter(new String[]{"No se pudieron cargar"}));
                        buildSpinner.setAdapter(adapter(new String[]{"Sin builds"}));
                        showError("No se pudieron consultar las versiones: " + exception.getMessage());
                    }
                });
            }
        });
    }

    private void loadBuilds(
            String software,
            String version,
            Spinner buildSpinner,
            List<MinecraftCatalog.Build> selectedBuilds,
            TextView buildLabel) {
        int request = buildRequests.incrementAndGet();
        buildSpinner.setAdapter(adapter(new String[]{"Cargando builds…"}));
        selectedBuilds.clear();
        io.execute(() -> {
            try {
                List<MinecraftCatalog.Build> values = MinecraftCatalog.builds(software, version);
                mainHandler.post(() -> {
                    if (request != buildRequests.get() || isFinishing()) {
                        return;
                    }
                    selectedBuilds.addAll(values);
                    String[] labels = new String[values.size()];
                    for (int index = 0; index < values.size(); index++) {
                        labels[index] = "Build " + values.get(index).id;
                    }
                    buildSpinner.setAdapter(adapter(labels));
                    buildLabel.setText(LocalServer.VANILLA.equals(software) ? "Canal" : "Build");
                });
            } catch (Exception exception) {
                mainHandler.post(() -> {
                    if (request == buildRequests.get()) {
                        buildSpinner.setAdapter(adapter(new String[]{"No se pudieron cargar"}));
                        showError("No se pudieron consultar las builds: " + exception.getMessage());
                    }
                });
            }
        });
    }

    private void installServer(
            LocalServer server,
            MinecraftCatalog.Build build,
            TermuxCommandClient.Callback callback) {
        String directory = "nexorypanel/servers/" + server.id;
        StringBuilder script = new StringBuilder()
                .append("set -eu\n")
                .append("server_dir=\"$HOME/").append(directory).append("\"\n")
                .append("mkdir -p \"$server_dir\"\n")
                .append("cd \"$server_dir\"\n")
                .append("rm -f .server.jar.download\n")
                .append("if ! curl --fail --location --retry 3 --connect-timeout 20 --max-time 1800 ")
                .append("--output .server.jar.download ")
                .append(shellQuote(build.downloadUrl)).append("; then\n")
                .append("  rm -f .server.jar.download\n")
                .append("  exit 1\n")
                .append("fi\n");
        if (!build.checksum.isEmpty()) {
            String command = "sha256sum";
            if ("sha1".equals(build.checksumAlgorithm)) {
                command = "sha1sum";
            }
            script.append("actual=$(").append(command)
                    .append(" .server.jar.download | cut -d ' ' -f 1)\n")
                    .append("[ \"$actual\" = ").append(shellQuote(build.checksum))
                    .append(" ] || { rm -f .server.jar.download; echo 'La comprobación SHA falló.' >&2; exit 1; }\n");
        }
        script.append("mv .server.jar.download server.jar\n")
                .append("printf 'eula=true\\n' > eula.txt\n")
                .append("printf 'server-port=").append(server.port)
                .append("\\n' > server.properties\n")
                .append("printf 'Servidor Nexory listo: ").append(server.software)
                .append(" ").append(server.version).append("\\n'\n");
        runTermuxScript(script.toString(), callback);
    }

    private void startServer(LocalServer server, TermuxCommandClient.Callback callback) {
        String directory = "nexorypanel/servers/" + server.id;
        String session = shellQuote(server.termuxSessionName());
        String script = "set -eu\n"
                + "server_dir=\"$HOME/" + directory + "\"\n"
                + "cd \"$server_dir\"\n"
                + "if tmux has-session -t " + session + " 2>/dev/null; then\n"
                + "  echo 'El servidor ya está en ejecución.'\n"
                + "  exit 0\n"
                + "fi\n"
                + "tmux new-session -d -s " + session + " -c \"$server_dir\""
                + " " + shellQuote("exec java -Xms256M -Xmx" + server.ramMb
                + "M -jar server.jar nogui") + "\n";
        runTermuxScript(script, callback);
    }

    private void stopServer(LocalServer server, TermuxCommandClient.Callback callback) {
        String session = shellQuote(server.termuxSessionName());
        runTermuxScript("set -eu\n"
                + "tmux send-keys -t " + session + " stop Enter\n",
                callback);
    }

    private void showConsole(LocalServer server) {
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16), dp(8), dp(16), dp(10));

        TextView status = text("Conectando con Termux…", 12, MUTED, false);
        content.addView(status, matchWrap());

        ScrollView logScroll = new ScrollView(this);
        TextView log = text("", 12, Color.rgb(223, 218, 237), false);
        log.setTypeface(Typeface.MONOSPACE);
        log.setTextIsSelectable(true);
        log.setPadding(dp(10), dp(10), dp(10), dp(10));
        log.setBackground(rounded(Color.rgb(12, 10, 19), dp(10), SURFACE_ALT));
        logScroll.addView(log, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        LinearLayout.LayoutParams logParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(300));
        logParams.topMargin = dp(8);
        content.addView(logScroll, logParams);

        LinearLayout commandRow = new LinearLayout(this);
        commandRow.setGravity(Gravity.CENTER_VERTICAL);
        EditText command = field("Comando del servidor", InputType.TYPE_CLASS_TEXT);
        command.setSingleLine(true);
        commandRow.addView(command, new LinearLayout.LayoutParams(0, dp(48), 1f));
        Button send = button("Enviar");
        LinearLayout.LayoutParams sendParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                dp(48));
        sendParams.leftMargin = dp(8);
        commandRow.addView(send, sendParams);
        LinearLayout.LayoutParams commandParams = matchWrap();
        commandParams.topMargin = dp(9);
        content.addView(commandRow, commandParams);

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Consola • " + server.name)
                .setView(content)
                .setPositiveButton("Cerrar", null)
                .create();
        Runnable[] poll = new Runnable[1];
        poll[0] = new Runnable() {
            @Override
            public void run() {
                captureConsole(server, result -> {
                    if (result.succeeded()) {
                        status.setText("Actualizado desde la sesión tmux.");
                        status.setTextColor(SUCCESS);
                        log.setText(result.stdout.trim().isEmpty()
                                ? "La consola no tiene salida reciente."
                                : result.stdout);
                        logScroll.post(() -> logScroll.fullScroll(View.FOCUS_DOWN));
                    } else {
                        status.setText(result.describeFailure());
                        status.setTextColor(ERROR);
                    }
                    if (dialog.isShowing()) {
                        mainHandler.postDelayed(poll[0], 3000);
                    }
                });
            }
        };
        send.setOnClickListener(view -> {
            String line = command.getText().toString().trim();
            if (line.isEmpty() || line.contains("\n") || line.contains("\r")) {
                showError("Escribe un solo comando en una línea.");
                return;
            }
            send.setEnabled(false);
            sendServerCommand(server, line, result -> {
                send.setEnabled(true);
                if (!result.succeeded()) {
                    showError(result.describeFailure());
                } else {
                    command.setText("");
                    mainHandler.post(poll[0]);
                }
            });
        });
        dialog.setOnShowListener(ignored -> {
            mainHandler.post(poll[0]);
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setTextColor(TEXT);
        });
        dialog.setOnDismissListener(ignored -> mainHandler.removeCallbacks(poll[0]));
        dialog.show();
    }

    private void captureConsole(LocalServer server, TermuxCommandClient.Callback callback) {
        String session = shellQuote(server.termuxSessionName());
        runTermuxScript("set -eu\n"
                + "tmux capture-pane -p -t " + session + " -S -180\n",
                callback);
    }

    private void sendServerCommand(
            LocalServer server,
            String command,
            TermuxCommandClient.Callback callback) {
        String session = shellQuote(server.termuxSessionName());
        String script = "set -eu\n"
                + "tmux send-keys -l -t " + session + " " + shellQuote(command) + "\n"
                + "tmux send-keys -t " + session + " Enter\n";
        runTermuxScript(script, callback);
    }

    private void confirmDeleteServer(LocalServer server) {
        new AlertDialog.Builder(this)
                .setTitle("Eliminar servidor")
                .setMessage("Se borrará el servidor y todos sus archivos de Termux. Esta acción no se puede deshacer.")
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Eliminar", (dialog, which) -> deleteServer(server))
                .show();
    }

    private void deleteServer(LocalServer server) {
        String directory = "nexorypanel/servers/" + server.id;
        String session = shellQuote(server.termuxSessionName());
        String script = "set -eu\n"
                + "tmux kill-session -t " + session + " 2>/dev/null || true\n"
                + "rm -rf -- \"$HOME/" + directory + "\"\n";
        runTermuxScript(script, result -> {
            if (!result.succeeded()) {
                showError(result.describeFailure());
                return;
            }
            servers.remove(server);
            try {
                serverStore.save(servers);
            } catch (IllegalStateException exception) {
                servers.add(server);
                showError(exception.getMessage());
                return;
            }
            showHome();
            showToast("Servidor eliminado.");
        });
    }

    private void installTermuxPackages() {
        if (!TermuxCommandClient.isInstalled(this)) {
            showTermuxInstructions();
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Instalar runtime Java")
                .setMessage("Termux descargará OpenJDK 25, tmux y curl. El proceso puede tardar y requiere conexión a Internet.")
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Continuar", (dialog, which) -> {
                    LinearLayout progressContent = new LinearLayout(this);
                    progressContent.setGravity(Gravity.CENTER_VERTICAL);
                    progressContent.setPadding(dp(20), dp(12), dp(20), dp(12));
                    ProgressBar progress = new ProgressBar(this);
                    progressContent.addView(progress, new LinearLayout.LayoutParams(dp(32), dp(32)));
                    TextView progressText = text(
                            "Instalando Java 25, tmux y curl en Termux…",
                            14,
                            TEXT,
                            false);
                    LinearLayout.LayoutParams progressTextParams = new LinearLayout.LayoutParams(
                            0,
                            ViewGroup.LayoutParams.WRAP_CONTENT,
                            1f);
                    progressTextParams.leftMargin = dp(14);
                    progressContent.addView(progressText, progressTextParams);
                    AlertDialog progressDialog = new AlertDialog.Builder(this)
                            .setTitle("Preparando el runtime")
                            .setView(progressContent)
                            .setCancelable(false)
                            .create();
                    progressDialog.show();
                    String script = "set -eu\n"
                            + "pkg update -y\n"
                            + "pkg install -y openjdk-25 tmux curl\n"
                            + "java -version\n"
                            + "tmux -V\n";
                    runTermuxScript(script, result -> {
                        progressDialog.dismiss();
                        if (!result.succeeded()) {
                            showError(result.describeFailure()
                                    + "\n\nAbre Termux, completa su configuración inicial y vuelve a intentar.");
                        } else {
                            showToast("Java 25, tmux y curl quedaron instalados en Termux.");
                        }
                    });
                })
                .show();
    }

    private void showTermuxInstructions() {
        String message = TermuxCommandClient.isInstalled(this)
                ? "Termux debe permitir comandos externos para que Nexory controle sus procesos.\n\n"
                + "1. Abre Termux al menos una vez y completa su configuración inicial.\n"
                + "2. En Termux, abre Settings y activa “Allow external apps”, o añade "
                + "allow-external-apps=true a ~/.termux/termux.properties.\n"
                + "3. En Android, abre Ajustes → Aplicaciones → NexoryPanel → Permisos adicionales "
                + "y permite “Run commands in Termux environment”.\n"
                + "4. Vuelve aquí y pulsa “Instalar Java”.\n\n"
                + "Si no ves un ajuste para apps externas, ejecuta en Termux: "
                + "mkdir -p ~/.termux && printf '\\nallow-external-apps=true\\n' >> ~/.termux/termux.properties\n\n"
                + "Usa Termux 0.109 o posterior, instalado desde F-Droid o su GitHub oficial. "
                + "No fuerces la detención de Termux mientras un servidor esté activo. Si Android lo cierra "
                + "al apagar la pantalla, quita Termux de la optimización de batería."
                : "Instala Termux desde F-Droid o desde las versiones oficiales de GitHub. "
                + "Después, ábrelo una vez y completa su configuración inicial. Nexory necesita "
                + "Termux 0.109 o posterior para ejecutar OpenJDK, tmux y los servidores.";
        AlertDialog.Builder builder = new AlertDialog.Builder(this)
                .setTitle("Preparar Termux")
                .setMessage(message)
                .setPositiveButton("Entendido", null);
        if (!TermuxCommandClient.isInstalled(this)) {
            builder.setNeutralButton("Descargar Termux", (dialog, which) -> openTermuxDownload());
        } else {
            builder.setNeutralButton("Abrir permisos", (dialog, which) -> openAppSettings());
            builder.setNegativeButton("Abrir Termux", (dialog, which) -> openTermux());
        }
        builder.show();
    }

    private void openAppSettings() {
        Intent intent = new Intent(
                android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + getPackageName()));
        startActivity(intent);
    }

    private void openTermux() {
        Intent intent = getPackageManager().getLaunchIntentForPackage(TermuxCommandClient.PACKAGE_NAME);
        if (intent == null) {
            showError("No se pudo abrir Termux. Comprueba que siga instalado.");
            return;
        }
        startActivity(intent);
    }

    private void openTermuxDownload() {
        Intent intent = new Intent(
                Intent.ACTION_VIEW,
                Uri.parse("https://f-droid.org/packages/com.termux/"));
        startActivity(intent);
    }

    private void runTermuxScript(String script, TermuxCommandClient.Callback callback) {
        if (!TermuxCommandClient.isInstalled(this)) {
            callback.onResult(new TermuxCommandClient.Result(
                    -1, 0, "", "", "Termux no está instalado. Instálalo desde F-Droid."));
            return;
        }
        TermuxCommandClient.runScript(
                this,
                script,
                TermuxCommandClient.HOME,
                result -> mainHandler.post(() -> callback.onResult(result)));
    }

    private void showError(String message) {
        new AlertDialog.Builder(this)
                .setTitle("No se pudo completar")
                .setMessage(message == null || message.trim().isEmpty()
                        ? "Se produjo un error inesperado."
                        : message)
                .setPositiveButton("Cerrar", null)
                .show();
    }

    private void showToast(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private String softwareKey(int position) {
        if (position == 1) {
            return LocalServer.PAPER;
        }
        if (position == 2) {
            return LocalServer.PURPUR;
        }
        return LocalServer.VANILLA;
    }

    private String softwareName(String software) {
        if (LocalServer.PAPER.equals(software)) {
            return "PaperMC";
        }
        if (LocalServer.PURPUR.equals(software)) {
            return "PurpurMC";
        }
        return "Vanilla";
    }

    private int maximumServerHeapMb() {
        ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
        manager.getMemoryInfo(memory);
        return Math.min(16384, Math.max(512, (int) (memory.totalMem / (1024 * 1024) * 0.7)));
    }

    private int nextAvailablePort() {
        int port = LocalServer.DEFAULT_PORT;
        while (port < 65535 && isPortInUse(port)) {
            port++;
        }
        return port;
    }

    private boolean isPortInUse(int port) {
        for (LocalServer server : servers) {
            if (server.port == port) {
                return true;
            }
        }
        return false;
    }

    private String shellQuote(String value) {
        return "'" + value.replace("'", "'\\''") + "'";
    }

    private TextView text(String value, int size, int color, boolean bold) {
        TextView result = new TextView(this);
        result.setText(value);
        result.setTextColor(color);
        result.setTextSize(size);
        if (bold) {
            result.setTypeface(null, Typeface.BOLD);
        }
        return result;
    }

    private EditText field(String hint, int inputType) {
        EditText result = new EditText(this);
        result.setSingleLine(true);
        result.setHint(hint);
        result.setHintTextColor(MUTED);
        result.setTextColor(TEXT);
        result.setTextSize(14);
        result.setInputType(inputType);
        result.setPadding(dp(12), dp(10), dp(12), dp(10));
        result.setBackground(rounded(SURFACE_ALT, dp(10), Color.rgb(72, 59, 96)));
        return result;
    }

    private Spinner spinner() {
        Spinner result = new Spinner(this);
        result.setBackground(rounded(SURFACE_ALT, dp(10), Color.rgb(72, 59, 96)));
        result.setPadding(dp(8), dp(4), dp(8), dp(4));
        return result;
    }

    private ArrayAdapter<String> adapter(String[] values) {
        ArrayAdapter<String> result = new ArrayAdapter<String>(
                this,
                android.R.layout.simple_spinner_item,
                values) {
            @Override
            public View getView(int position, View convertView, ViewGroup parent) {
                TextView item = (TextView) super.getView(position, convertView, parent);
                item.setTextColor(TEXT);
                item.setPadding(dp(8), dp(8), dp(8), dp(8));
                return item;
            }

            @Override
            public View getDropDownView(int position, View convertView, ViewGroup parent) {
                TextView item = (TextView) super.getDropDownView(position, convertView, parent);
                item.setTextColor(TEXT);
                item.setBackgroundColor(SURFACE_ALT);
                item.setPadding(dp(12), dp(12), dp(12), dp(12));
                return item;
            }
        };
        result.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        return result;
    }

    private Button button(String label) {
        Button result = new Button(this);
        result.setText(label);
        result.setTextColor(TEXT);
        result.setTextSize(14);
        result.setAllCaps(false);
        result.setPadding(dp(10), dp(7), dp(10), dp(7));
        result.setBackground(rounded(PRIMARY, dp(12), PRIMARY));
        return result;
    }

    private Button secondaryButton(String label) {
        Button result = button(label);
        result.setBackground(rounded(SURFACE_ALT, dp(12), SURFACE_ALT));
        return result;
    }

    private GradientDrawable rounded(int fill, int radius, int stroke) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(radius);
        drawable.setStroke(dp(1), stroke);
        return drawable;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
