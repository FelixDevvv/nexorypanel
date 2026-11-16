package com.felixdevvv.nexorypanel;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public final class TermuxCommandResultReceiver extends BroadcastReceiver {
    static final String EXTRA_EXECUTION_ID = "nexory.execution_id";

    private static final String RESULT_BUNDLE = "result";
    private static final String RESULT_STDOUT = "stdout";
    private static final String RESULT_STDERR = "stderr";
    private static final String RESULT_EXIT_CODE = "exitCode";
    private static final String RESULT_ERROR = "err";
    private static final String RESULT_ERROR_MESSAGE = "errmsg";
    private static final Map<Integer, TermuxCommandClient.Callback> CALLBACKS =
            new ConcurrentHashMap<>();

    static void register(int executionId, TermuxCommandClient.Callback callback) {
        if (callback != null) {
            CALLBACKS.put(executionId, callback);
        }
    }

    static void fail(int executionId, RuntimeException exception) {
        TermuxCommandClient.Callback callback = CALLBACKS.remove(executionId);
        if (callback != null) {
            callback.onResult(new TermuxCommandClient.Result(
                    -1,
                    0,
                    "",
                    "",
                    exception.getMessage() == null
                            ? "No se pudo contactar con Termux."
                            : exception.getMessage()));
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        int executionId = intent.getIntExtra(EXTRA_EXECUTION_ID, -1);
        TermuxCommandClient.Callback callback = CALLBACKS.remove(executionId);
        if (callback == null) {
            return;
        }
        Bundle result = intent.getBundleExtra(RESULT_BUNDLE);
        if (result == null) {
            callback.onResult(new TermuxCommandClient.Result(
                    -1, 0, "", "", "Termux no devolvió el resultado del comando."));
            return;
        }
        callback.onResult(new TermuxCommandClient.Result(
                result.getInt(RESULT_EXIT_CODE, -1),
                result.getInt(RESULT_ERROR, 0),
                result.getString(RESULT_STDOUT, ""),
                result.getString(RESULT_STDERR, ""),
                result.getString(RESULT_ERROR_MESSAGE, "")));
    }
}
