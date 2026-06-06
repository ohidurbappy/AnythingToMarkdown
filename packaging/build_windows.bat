@echo off
REM Build the clickable AnythingToMarkdown app for Windows.
REM Produces a single-file executable: dist\AnythingToMarkdown.exe
setlocal

set "HERE=%~dp0"
set "ROOT=%HERE%.."
set "VENV=%ROOT%\.venv"
set "PY=%VENV%\Scripts\python.exe"

if not exist "%PY%" (
    echo Error: virtual environment not found at %VENV% >&2
    echo Run "make install" once first to create it. >&2
    exit /b 1
)

"%PY%" -m pip install --quiet pyinstaller || exit /b 1

pushd "%HERE%"
"%VENV%\Scripts\pyinstaller.exe" AnythingToMarkdown.spec ^
    --noconfirm --clean ^
    --distpath "%ROOT%\dist" --workpath "%ROOT%\build"
set "RC=%ERRORLEVEL%"
popd

if not "%RC%"=="0" exit /b %RC%

echo.
echo Built: %ROOT%\dist\AnythingToMarkdown.exe
echo Double-click AnythingToMarkdown.exe to launch the GUI.
endlocal
