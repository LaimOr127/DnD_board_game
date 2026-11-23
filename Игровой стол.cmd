@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python
py -3 site\server.py --bind 0.0.0.0 --open
goto done
:python
python site\server.py --bind 0.0.0.0 --open
:done
if errorlevel 1 pause
