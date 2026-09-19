/*
 * Web-side ad bridge.
 *
 * Inside the Android app this talks to AdHost.java over the "AndroidAds"
 * JavaScript interface: a docked adaptive banner (which needs no code here at
 * all - it is laid out below the WebView), plus interstitial and rewarded ads
 * the game asks for at its own natural break points.
 *
 * Loaded as a plain web page there is no bridge, so every call is a no-op that
 * still runs your callback. Nothing here touches the DOM, so it is safe to drop
 * into any of the apps without matching their markup.
 *
 * Typical use:
 *   Ads.interstitial();                 // at a natural break - level end, game over
 *   Ads.rewarded(() => addCoins(20));   // only ever from an explicit user tap
 */
window.Ads = (function () {
  'use strict';

  var bridge = null;
  try {
    if (window.AndroidAds && window.AndroidAds.available()) bridge = window.AndroidAds;
  } catch (e) {
    bridge = null;
  }

  var cfg = {
    // Interstitials are frequency-capped here rather than at the call site, so
    // sprinkling Ads.interstitial() through a game cannot turn into ad spam.
    // Google demotes apps that show them too often, and players uninstall.
    minGapMs: 120000,   // at least two minutes between interstitials
    warmupMs: 60000,    // never in the first minute of a session
  };

  var launchedAt = Date.now();
  var lastInterstitial = 0;
  var rewardCb = null;

  function call(name) {
    if (!bridge) return null;
    var args = Array.prototype.slice.call(arguments, 1);
    try {
      return bridge[name].apply(bridge, args);
    } catch (e) {
      return null;
    }
  }

  /* Called from AdHost.java when an ad is shown, fails, or is dismissed. */
  window.__adCallback = function (kind, ok) {
    if (kind !== 'reward') return;
    var cb = rewardCb;
    rewardCb = null;
    if (ok && cb) cb();
  };

  return {
    /** True when running inside the app with the native SDK behind it. */
    get native() { return !!bridge; },

    /** Override the interstitial pacing. Called before the first interstitial. */
    configure: function (opts) {
      for (var k in opts) if (opts.hasOwnProperty(k)) cfg[k] = opts[k];
    },

    /**
     * Show an interstitial if one is loaded and the frequency cap allows it.
     * Safe to call at every level end - it declines quietly when too soon.
     * Returns true only if an ad was actually requested.
     */
    interstitial: function () {
      if (!bridge) return false;
      var now = Date.now();
      if (now - launchedAt < cfg.warmupMs) return false;
      if (now - lastInterstitial < cfg.minGapMs) return false;
      if (!call('interstitialReady')) return false;
      lastInterstitial = now;
      call('showInterstitial');
      return true;
    },

    /** True when a rewarded ad is loaded - use it to enable/hide the button. */
    rewardedReady: function () {
      return !!call('rewardedReady');
    },

    /**
     * Play a rewarded ad, then run onReward if the user actually earned it.
     * Only ever call this from a deliberate tap on a "watch an ad" control.
     * On the web (no bridge) the reward is granted immediately so the feature
     * stays testable in a browser.
     */
    rewarded: function (onReward) {
      if (!bridge) {
        if (onReward) onReward();
        return;
      }
      rewardCb = onReward || null;
      call('showRewarded');
    },

    /** Hide the docked banner for good - e.g. after a Remove Ads purchase. */
    setBannerEnabled: function (on) {
      call('setBannerEnabled', !!on);
    },

    /**
     * True where the user is legally entitled to revisit their consent choice
     * (the EEA and the UK). Use it to show a "Privacy settings" row in your own
     * settings screen; the app already docks a fallback link above the banner,
     * so wiring this is optional.
     */
    privacyOptionsRequired: function () {
      return !!call('privacyOptionsRequired');
    },

    /** Reopen the consent form so the user can change or withdraw consent. */
    showPrivacyOptions: function () {
      call('showPrivacyOptions');
    },
  };
})();
