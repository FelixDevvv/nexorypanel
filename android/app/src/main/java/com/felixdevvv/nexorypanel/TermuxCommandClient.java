package com.felixdevvv.nexorypanel;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;

import java.util.concurrent.atomic.AtomicInteger;

final class TermuxCommandClient {
    static final String PACKAGE_NAME = "com.termux";
    static final String HOME = "~/";
    static final String PREFIX = "$PREFIX";

    interface Callback {
        void onResult(Result result);
    }

    static final class Result {
        final int exitCode;
        final int internalError;
        final String stdout;
        final String stderr;
        final String errorMessage;

        Result(int exitCode, int internalError, String stdout, String stderr, String errorMessage) {
            this.exitCode = exitCode;
            this.internalError = internalError;
            this.stdout = stdout;
            this.stderr = stderr;
            this.errorMessage = errorMessage;
        }

        boolean succeeded() {
            return exitCode == 0 && internalError == -1;
        }

        String describeFailure() {
            if (internalError != -1) {
                return errorMessage.isEmpty()
                        ? "Termux no pudo ejecutar el comando. Comprueba los permisos y su configuración."
                        : errorMessage;
            }
            String output = stderr.isEmpty() ? stdout : stderr;
            return output.trim().isEmpty()
                    ? "El comando de Termux terminó con código " + exitCode + "."
                    : output.trim();
        }
    }

    private static final AtomicInteger NEXT_ID = new AtomicInteger(1000);

    private TermuxCommandClient() {}

    static boolean isInstalled(Context context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                context.getPackageManager().getPackageInfo(
                        PACKAGE_NAME,
                        PackageManager.PackageInfoFlags.of(0));
            } else {
                context.getPackageManager().getPackageInfo(PACKAGE_NAME, 0);
            }
            return true;
        } catch (PackageManager.NameNotFoundException exception) {
            return false;
        }
    }

    static void runScript(Context context, String script, String workDirectory, Callback callback) {
        run(context,
                PREFIX + "/bin/bash",
                new String[]{"-s"},
                script,
                workDirectory,
                callback);
    }

    static void run(
            Context context,
            String commandPath,
            String[] arguments,
            String stdin,
            String workDirectory,
            Callback callback) {
        int executionId = NEXT_ID.incrementAndGet();
        TermuxCommandResultReceiver.register(executionId, callback);

        Intent resultIntent = new Intent(context, TermuxCommandResultReceiver.class);
        resultIntent.putExtra(TermuxCommandResultReceiver.EXTRA_EXECUTION_ID, executionId);
        int pendingIntentFlags = PendingIntent.FLAG_ONE_SHOT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            pendingIntentFlags |= PendingIntent.FLAG_MUTABLE;
        }
        PendingIntent pendingIntent = PendingIntent.getBroadcast(
                context,
                executionId,
                resultIntent,
                pendingIntentFlags);

        Intent command = new Intent("com.termux.RUN_COMMAND");
        command.setClassName(PACKAGE_NAME, "com.termux.app.RunCommandService");
        command.putExtra("com.termux.RUN_COMMAND_PATH", commandPath);
        command.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", arguments);
        command.putExtra("com.termux.RUN_COMMAND_BACKGROUND", true);
        command.putExtra("com.termux.RUN_COMMAND_WORKDIR", workDirectory);
        if (stdin != null) {
            command.putExtra("com.termux.RUN_COMMAND_STDIN", stdin);
        }
        command.putExtra("com.termux.RUN_COMMAND_PENDING_INTENT", pendingIntent);

        try {
            context.startService(command);
        } catch (RuntimeException exception) {
            TermuxCommandResultReceiver.fail(executionId, exception);
        }
    }
}
