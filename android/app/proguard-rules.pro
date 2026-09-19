# WebView JavaScript bridges are invoked by name from JavaScript, so R8 cannot see a
# caller for them and would otherwise rename or strip them outright. This rule is the
# reason the ad and clipboard bridges keep working in release builds.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
# Room builds its database by reflecting on a generated <Name>_Impl class, so R8 sees no
# reference to it and strips it. Play Services ads pulls in WorkManager, which is backed
# by a Room database - without this the app dies at startup inside
# androidx.startup.InitializationProvider, long before any of our code runs.
-keep class * extends androidx.room.RoomDatabase { <init>(); }
