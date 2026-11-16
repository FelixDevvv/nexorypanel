package com.felixdevvv.nexorypanel;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.SslErrorHandler;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;

public final class MainActivity extends Activity {
    private static final String PREFERENCES = "nexory-panel";
    private static final String PANEL_URL_KEY = "panel-url";
    private static final int FILE_CHOOSER_REQUEST = 10;

    private final int backgroundColor = Color.rgb(17, 16, 27);
    private final int surfaceColor = Color.rgb(27, 25, 40);
    private final int primaryColor = Color.rgb(168, 85, 247);
    private final int textColor = Color.rgb(247, 244, 255);
    private final int mutedColor = Color.rgb(184, 177, 201);

    private FrameLayout root;
    private WebView panelWebView;
    private ProgressBar pageProgress;
    private String panelBaseUrl;
    private ValueCallback<Uri[]> pendingFileChooser;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(backgroundColor);
        window.setNavigationBarColor(backgroundColor);
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);

        SharedPreferences preferences = getSharedPreferences(PREFERENCES, MODE_PRIVATE);
        String savedUrl = preferences.getString(PANEL_URL_KEY, "");
        if (savedUrl == null || savedUrl.isEmpty()) {
            showConnectionScreen("", null);
        } else {
            String normalized = PanelUrl.normalize(savedUrl);
            if (normalized == null) {
                showConnectionScreen(savedUrl, "La dirección guardada no es válida.");
            } else {
                connectToPanel(normalized);
            }
        }
    }

    private void showConnectionScreen(String value, String error) {
        panelBaseUrl = null;
        if (panelWebView != null) {
            panelWebView.stopLoading();
            panelWebView.destroy();
            panelWebView = null;
        }

        root = new FrameLayout(this);
        root.setBackgroundColor(backgroundColor);
        ScrollView scrollView = new ScrollView(this);
        scrollView.setFillViewport(true);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setGravity(Gravity.CENTER_HORIZONTAL);
        content.setPadding(dp(28), dp(44), dp(28), dp(32));

        ImageView logo = new ImageView(this);
        logo.setImageResource(R.mipmap.ic_launcher);
        logo.setScaleType(ImageView.ScaleType.FIT_CENTER);
        LinearLayout.LayoutParams logoParams = new LinearLayout.LayoutParams(dp(88), dp(88));
        logoParams.bottomMargin = dp(18);
        content.addView(logo, logoParams);

        TextView heading = new TextView(this);
        heading.setText("Conecta tu panel");
        heading.setTextColor(textColor);
        heading.setTextSize(27);
        heading.setTypeface(null, android.graphics.Typeface.BOLD);
        heading.setGravity(Gravity.CENTER);
        content.addView(heading, matchWrap());

        TextView description = new TextView(this);
        description.setText("Accede a NexoryPanel desde tu teléfono. Introduce la dirección HTTPS del panel que ya tienes alojado.");
        description.setTextColor(mutedColor);
        description.setTextSize(15);
        description.setGravity(Gravity.CENTER);
        description.setLineSpacing(dp(4), 1f);
        LinearLayout.LayoutParams descriptionParams = matchWrap();
        descriptionParams.topMargin = dp(12);
        descriptionParams.bottomMargin = dp(28);
        content.addView(description, descriptionParams);

        TextView label = new TextView(this);
        label.setText("Dirección del panel");
        label.setTextColor(textColor);
        label.setTextSize(14);
        label.setTypeface(null, android.graphics.Typeface.BOLD);
        content.addView(label, matchWrap());

        EditText address = new EditText(this);
        address.setSingleLine(true);
        address.setText(value);
        address.setHint("https://panel.ejemplo.com");
        address.setHintTextColor(mutedColor);
        address.setTextColor(textColor);
        address.setTextSize(15);
        address.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        address.setSelectAllOnFocus(true);
        address.setPadding(dp(14), dp(12), dp(14), dp(12));
        address.setBackground(roundedBackground(surfaceColor, dp(12), Color.rgb(62, 54, 80)));
        LinearLayout.LayoutParams addressParams = matchWrap();
        addressParams.topMargin = dp(9);
        content.addView(address, addressParams);

        TextView errorText = new TextView(this);
        errorText.setTextColor(Color.rgb(255, 139, 151));
        errorText.setTextSize(13);
        errorText.setVisibility(error == null ? View.GONE : View.VISIBLE);
        errorText.setText(error == null ? "" : error);
        LinearLayout.LayoutParams errorParams = matchWrap();
        errorParams.topMargin = dp(8);
        content.addView(errorText, errorParams);

        Button connectButton = button("Conectar");
        LinearLayout.LayoutParams buttonParams = matchWrap();
        buttonParams.topMargin = dp(20);
        content.addView(connectButton, buttonParams);
        connectButton.setOnClickListener(view -> {
            String normalized = PanelUrl.normalize(address.getText().toString());
            if (normalized == null) {
                errorText.setText("Usa una dirección HTTPS válida, sin usuario, contraseña ni parámetros.");
                errorText.setVisibility(View.VISIBLE);
                return;
            }
            getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                    .edit()
                    .putString(PANEL_URL_KEY, normalized)
                    .apply();
            connectToPanel(normalized);
        });

        TextView securityNote = new TextView(this);
        securityNote.setText("La app solo carga páginas HTTPS del mismo dominio configurado. No aloja servidores Minecraft dentro del teléfono.");
        securityNote.setTextColor(mutedColor);
        securityNote.setTextSize(12);
        securityNote.setGravity(Gravity.CENTER);
        securityNote.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams noteParams = matchWrap();
        noteParams.topMargin = dp(24);
        content.addView(securityNote, noteParams);

        scrollView.addView(content);
        root.addView(scrollView);
        setContentView(root);
    }

    private void connectToPanel(String normalizedUrl) {
        panelBaseUrl = normalizedUrl;
        root = new FrameLayout(this);
        root.setBackgroundColor(backgroundColor);

        LinearLayout screen = new LinearLayout(this);
        screen.setOrientation(LinearLayout.VERTICAL);
        root.addView(screen, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        LinearLayout toolbar = new LinearLayout(this);
        toolbar.setGravity(Gravity.CENTER_VERTICAL);
        toolbar.setPadding(dp(16), dp(8), dp(10), dp(8));
        toolbar.setBackgroundColor(surfaceColor);

        TextView title = new TextView(this);
        title.setText("NexoryPanel");
        title.setTextColor(textColor);
        title.setTextSize(17);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        toolbar.addView(title, new LinearLayout.LayoutParams(0, dp(44), 1f));

        Button changePanelButton = button("Cambiar panel");
        changePanelButton.setTextSize(12);
        toolbar.addView(changePanelButton, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                dp(42)));
        changePanelButton.setOnClickListener(
                view -> showConnectionScreen(panelBaseUrl, null));
        screen.addView(toolbar, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(60)));

        pageProgress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        pageProgress.setMax(100);
        pageProgress.setProgressTintList(android.content.res.ColorStateList.valueOf(primaryColor));
        pageProgress.setVisibility(View.GONE);
        screen.addView(pageProgress, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(3)));

        panelWebView = new WebView(this);
        configureWebView(panelWebView);
        screen.addView(panelWebView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1f));
        setContentView(root);
        panelWebView.loadUrl(normalizedUrl);
    }

    private void configureWebView(WebView webView) {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setSupportZoom(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setSupportMultipleWindows(false);
        settings.setSafeBrowsingEnabled(true);
        webView.setBackgroundColor(backgroundColor);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (PanelUrl.isAllowedNavigation(panelBaseUrl, request.getUrl().toString())) {
                    return false;
                }
                Toast.makeText(MainActivity.this,
                        "Se bloqueó una navegación fuera del panel HTTPS configurado.",
                        Toast.LENGTH_LONG).show();
                return true;
            }

            @Override
            public void onReceivedError(
                    WebView view,
                    WebResourceRequest request,
                    WebResourceError error) {
                if (request.isForMainFrame()) {
                    showConnectionScreen(panelBaseUrl, "No se pudo conectar. Comprueba la URL y la conexión.");
                }
            }

            @Override
            public void onReceivedSslError(
                    WebView view,
                    SslErrorHandler handler,
                    android.net.http.SslError error) {
                handler.cancel();
                Toast.makeText(MainActivity.this,
                        "Conexión bloqueada: el certificado HTTPS no es válido.",
                        Toast.LENGTH_LONG).show();
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int progress) {
                if (pageProgress == null) {
                    return;
                }
                pageProgress.setProgress(progress);
                pageProgress.setVisibility(progress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public boolean onShowFileChooser(
                    WebView view,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams) {
                if (pendingFileChooser != null) {
                    pendingFileChooser.onReceiveValue(null);
                }
                pendingFileChooser = filePathCallback;
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                try {
                    startActivityForResult(intent, FILE_CHOOSER_REQUEST);
                    return true;
                } catch (android.content.ActivityNotFoundException exception) {
                    pendingFileChooser = null;
                    filePathCallback.onReceiveValue(null);
                    Toast.makeText(MainActivity.this,
                            "No hay un selector de archivos disponible.",
                            Toast.LENGTH_SHORT).show();
                    return false;
                }
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FILE_CHOOSER_REQUEST || pendingFileChooser == null) {
            return;
        }
        Uri[] results = null;
        if (resultCode == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                ArrayList<Uri> uris = new ArrayList<>(count);
                for (int index = 0; index < count; index++) {
                    uris.add(data.getClipData().getItemAt(index).getUri());
                }
                results = uris.toArray(new Uri[0]);
            } else if (data.getData() != null) {
                results = new Uri[] {data.getData()};
            }
        }
        pendingFileChooser.onReceiveValue(results);
        pendingFileChooser = null;
    }

    @Override
    public void onBackPressed() {
        if (panelWebView != null && panelWebView.canGoBack()) {
            panelWebView.goBack();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (pendingFileChooser != null) {
            pendingFileChooser.onReceiveValue(null);
            pendingFileChooser = null;
        }
        if (panelWebView != null) {
            panelWebView.stopLoading();
            panelWebView.destroy();
            panelWebView = null;
        }
        super.onDestroy();
    }

    private Button button(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextColor(textColor);
        button.setTextSize(15);
        button.setAllCaps(false);
        button.setPadding(dp(16), dp(8), dp(16), dp(8));
        button.setBackground(roundedBackground(primaryColor, dp(12), primaryColor));
        return button;
    }

    private GradientDrawable roundedBackground(int fill, int radius, int stroke) {
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
