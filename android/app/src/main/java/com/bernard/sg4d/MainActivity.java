package com.bernard.sg4d;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.webkit.WebViewAssetLoader;

/**
 * Hosts the SG 4D web app in a WebView.
 *
 * Unlike the offline games in this collection, the page is NOT loaded from
 * file:///android_asset. It is served through a WebViewAssetLoader on
 * https://appassets.androidplatform.net, which maps that virtual host straight
 * back onto the same asset folder. The files are identical; the origin is not,
 * and the origin is the entire point:
 *
 *   - fetch() to the exchange-rate APIs is an ordinary CORS request from a real
 *     https origin. From a file:// page the origin is "null", which is a
 *     category of request several WebView versions decline outright — the app
 *     would open to an empty board on exactly the devices we cannot test on.
 *   - localStorage gets a stable, per-app origin, so cached rates, alerts and
 *     settings survive an update instead of living under the opaque file
 *     origin.
 *   - Service workers only register on a secure origin, so the offline cache
 *     works in the APK the same way it does on the web.
 */
public class MainActivity extends Activity {

    private static final String APP_URL =
            "https://appassets.androidplatform.net/assets/www/index.html";

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        final WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        // Nothing is read off the filesystem directly - the loader serves assets.
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
                // Only the virtual host is intercepted; requests to the results
                // feed fall through and go out over the network as normal.
                return loader.shouldInterceptRequest(req.getUrl());
            }
        });

        // The results feed cannot be fetched from JavaScript - Singapore Pools
        // sends no CORS header - so Java does it. Scoped to that one host and
        // asynchronous; see NetBridge.java.
        webView.addJavascriptInterface(new NetBridge(webView), "AndroidNet");

        // AdHost wraps the WebView so the banner docks below it, and owns the
        // "AndroidAds" bridge and the ad lifecycle. See AdHost.java.
        setContentView(new AdHost(this, webView).root());

        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState);
        } else {
            webView.loadUrl(APP_URL);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }
}
