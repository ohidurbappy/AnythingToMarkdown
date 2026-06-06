@echo off
REM Launch AnythingToMarkdown on Windows.
REM Sets up the virtual environment on first run, then forwards all arguments.
REM   run.bat                -> opens the GUI
REM   run.bat file.pdf       -> CLI: convert file.pdf
REM   run.bat --help         -> CLI help
setlocal
set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"

if not exist "%VENV%" (
    echo Setting up virtual environment ^(first run^)...
    where py >nul 2>nul
    if %ERRORLEVEL%==0 (
        py -3 -m venv "%VENV%"
    ) else (
        python -m venv "%VENV%"
    )
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV%\Scripts\python.exe" -m pip install -r "%ROOT%requirements.txt"
)

REM Use pythonw for the GUI (no console) when no arguments are passed.
if "%~1"=="" (
    start "" "%VENV%\Scripts\pythonw.exe" -m anytomd
) else (
    "%VENV%\Scripts\python.exe" -m anytomd %*
)
endlocal
