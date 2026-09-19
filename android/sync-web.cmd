@echo off
rem Re-copies the web app files into the APK assets. Run before rebuilding after web edits.
copy /Y "%~dp0..\index.html" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\style.css" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\ads.js" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\data.js" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\checker.js" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\stats.js" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\app.js" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\sw.js" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\manifest.webmanifest" "%~dp0app\src\main\assets\www\"
copy /Y "%~dp0..\data\history.json" "%~dp0app\src\main\assets\www\data\"
copy /Y "%~dp0..\icons\icon-192.png" "%~dp0app\src\main\assets\www\icons\"
copy /Y "%~dp0..\icons\icon-512.png" "%~dp0app\src\main\assets\www\icons\"
