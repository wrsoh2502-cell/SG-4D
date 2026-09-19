@echo off
cd /d "%~dp0"
python -m http.server 8134 --bind 127.0.0.1
