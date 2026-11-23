@echo off
REM Double-click to build EMLII.exe  (needs Python 3.9+ from python.org, with tcl/tk)
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -m pip install --upgrade pip pyinstaller flask
%PY% build_exe.py %*
echo.
pause
