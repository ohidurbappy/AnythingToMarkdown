@echo off
REM ===========================================================================
REM  AnythingToMarkdown - Windows task runner (no GNU Make required).
REM  Mirrors the Unix Makefile targets.  Usage:  make <target> [args]
REM
REM    make                 show help
REM    make venv            create the virtual environment
REM    make install         install runtime dependencies
REM    make dev             editable install (adds the `anytomd` command)
REM    make run             launch the GUI   (alias: make gui)
REM    make cli <args...>   run the CLI, e.g.  make cli report.pdf -o out
REM    make app             build the single-file Windows app (dist\AnythingToMarkdown.exe)
REM    make open-app        reveal the built executable in Explorer
REM    make icon            regenerate the app icons
REM    make msix            build the unsigned .msix for the Microsoft Store
REM    make msix-sideload   build a self-signed .msix you can install locally
REM    make msix-install    install the built .msix (run as Administrator)
REM    make msix-uninstall  remove the installed .msix
REM    make store-check     check the Store listing against Partner Center limits
REM    make version         print the current version
REM    make clean           remove build/dist artifacts (keeps the venv)
REM    make clean-all       also remove the virtual environment
REM ===========================================================================
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PIP=%PY% -m pip"
set "APP_NAME=AnythingToMarkdown"
set "STAMP=%VENV%\.installed"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=help"

if /I "%TARGET%"=="help"       goto :help
if /I "%TARGET%"=="venv"       goto :venv
if /I "%TARGET%"=="install"    goto :install
if /I "%TARGET%"=="dev"        goto :dev
if /I "%TARGET%"=="run"        goto :run
if /I "%TARGET%"=="gui"        goto :run
if /I "%TARGET%"=="cli"        goto :cli
if /I "%TARGET%"=="app"        goto :app
if /I "%TARGET%"=="open-app"   goto :open_app
if /I "%TARGET%"=="icon"       goto :icon
if /I "%TARGET%"=="msix"           goto :msix
if /I "%TARGET%"=="msix-payload"   goto :msix_payload
if /I "%TARGET%"=="msix-sideload"  goto :msix_sideload
if /I "%TARGET%"=="msix-install"   goto :msix_install
if /I "%TARGET%"=="msix-uninstall" goto :msix_uninstall
if /I "%TARGET%"=="msix-assets"    goto :msix_assets
if /I "%TARGET%"=="store-check"    goto :store_check
if /I "%TARGET%"=="version"        goto :version
if /I "%TARGET%"=="clean"      goto :clean
if /I "%TARGET%"=="clean-all"  goto :clean_all

echo Unknown target "%TARGET%".
echo.
goto :help

REM ---------------------------------------------------------------------------
:help
echo %APP_NAME% - available targets:
echo   help        Show this help
echo   venv        Create the virtual environment (if missing)
echo   install     Install runtime dependencies into the venv
echo   dev         Editable install so the `anytomd` command is available
echo   run / gui   Launch the GUI
echo   cli ARGS    Run the CLI, e.g. make cli report.pdf -o out
echo   app         Build the single-file Windows app (dist\%APP_NAME%.exe)
echo   open-app    Reveal the built executable in Explorer
echo   icon        Regenerate the app icons
echo   msix            Build the unsigned .msix for the Microsoft Store
echo   msix-payload    Build just the one-folder payload the .msix is packed from
echo   msix-sideload   Build a self-signed .msix that can be installed locally
echo   msix-install    Install the built .msix (needs an elevated prompt)
echo   msix-uninstall  Remove the installed .msix
echo   msix-assets     Regenerate the MSIX tile/logo images
echo   store-check     Check the Store listing against Partner Center limits
echo   version         Print the current version
echo   clean       Remove build/dist artifacts (keeps the venv)
echo   clean-all   Remove everything, including the virtual environment
goto :eof

REM ---------------------------------------------------------------------------
:venv
if exist "%PY%" (
    echo Virtual environment already exists.
    goto :eof
)
call :create_venv || exit /b 1
goto :eof

:create_venv
echo Creating virtual environment...
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 -m venv "%VENV%" || exit /b 1
) else (
    python -m venv "%VENV%" || exit /b 1
)
"%PY%" -m pip install --upgrade pip || exit /b 1
exit /b 0

REM ---------------------------------------------------------------------------
:install
if not exist "%PY%" ( call :create_venv || exit /b 1 )
if not exist "%STAMP%" (
    %PIP% install -r "%ROOT%requirements.txt" || exit /b 1
    echo done> "%STAMP%"
) else (
    echo Dependencies already installed ^(run "make clean-all" to reset^).
)
goto :eof

:ensure_install
if not exist "%PY%" ( call :create_venv || exit /b 1 )
if not exist "%STAMP%" (
    %PIP% install -r "%ROOT%requirements.txt" || exit /b 1
    echo done> "%STAMP%"
)
exit /b 0

REM ---------------------------------------------------------------------------
:dev
call :ensure_install || exit /b 1
%PIP% install -e "%ROOT%." || exit /b 1
goto :eof

REM ---------------------------------------------------------------------------
:run
call :ensure_install || exit /b 1
"%PY%" -m anytomd
goto :eof

REM ---------------------------------------------------------------------------
:cli
call :ensure_install || exit /b 1
REM Forward every argument after "cli" to the CLI.
set "ARGS=%*"
set "ARGS=!ARGS:*cli=!"
"%PY%" -m anytomd !ARGS!
goto :eof

REM ---------------------------------------------------------------------------
:app
call :ensure_install || exit /b 1
%PIP% install --quiet pyinstaller || exit /b 1
pushd "%ROOT%packaging"
"%VENV%\Scripts\pyinstaller.exe" %APP_NAME%.spec --noconfirm --clean ^
    --distpath "%ROOT%dist" --workpath "%ROOT%build"
popd
echo.
echo Built single-file executable: dist\%APP_NAME%.exe
echo Run it by double-clicking %APP_NAME%.exe, or: make open-app
goto :eof

REM ---------------------------------------------------------------------------
:open_app
if exist "%ROOT%dist\%APP_NAME%.exe" (
    explorer /select,"%ROOT%dist\%APP_NAME%.exe"
) else (
    echo Not built yet. Run "make app" first.
)
goto :eof

REM ---------------------------------------------------------------------------
:icon
call :ensure_install || exit /b 1
"%PY%" "%ROOT%packaging\make_icon.py"
echo Wrote packaging\AppIcon.ico (Windows) and AppIcon.iconset (macOS)
goto :eof

REM ---------------------------------------------------------------------------
REM  Microsoft Store / MSIX.  See packaging\msix\README.md.
REM ---------------------------------------------------------------------------
:msix_payload
call :ensure_install || exit /b 1
%PIP% install --quiet pyinstaller || exit /b 1
REM One-folder build: an MSIX ships an already-extracted app, so the
REM single-file bootloader's extract-to-temp step would be pure overhead.
set "BUILD_ONEDIR=1"
pushd "%ROOT%packaging"
"%VENV%\Scripts\pyinstaller.exe" %APP_NAME%.spec --noconfirm --clean ^
    --distpath "%ROOT%dist" --workpath "%ROOT%build"
set "RC=%ERRORLEVEL%"
popd
set "BUILD_ONEDIR="
if not "%RC%"=="0" exit /b %RC%
echo Built payload: dist\%APP_NAME%\
exit /b 0

:msix
call :msix_payload || exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%packaging\msix\build_msix.ps1" || exit /b 1
goto :eof

:msix_sideload
call :msix_payload || exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%packaging\msix\build_msix.ps1" -SelfSign || exit /b 1
goto :eof

:msix_install
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%packaging\msix\Install-Sideload.ps1"
goto :eof

:msix_uninstall
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%packaging\msix\Uninstall-AnythingToMarkdown.ps1"
goto :eof

:msix_assets
call :ensure_install || exit /b 1
"%PY%" "%ROOT%packaging\msix\make_msix_assets.py"
goto :eof

:store_check
call :ensure_install || exit /b 1
"%PY%" "%ROOT%packaging\msix\check_manifest.py" || exit /b 1
"%PY%" "%ROOT%store\validate_listing.py"
goto :eof

:version
call :ensure_install || exit /b 1
"%PY%" "%ROOT%packaging\version_tool.py" get
goto :eof

REM ---------------------------------------------------------------------------
:clean
if exist "%ROOT%build"            rmdir /s /q "%ROOT%build"
if exist "%ROOT%dist"             rmdir /s /q "%ROOT%dist"
if exist "%ROOT%anytomd.egg-info" rmdir /s /q "%ROOT%anytomd.egg-info"
if exist "%ROOT%packaging\AppIcon.iconset" rmdir /s /q "%ROOT%packaging\AppIcon.iconset"
for /d /r "%ROOT%" %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
echo Cleaned build/dist artifacts.
goto :eof

REM ---------------------------------------------------------------------------
:clean_all
call :clean
if exist "%VENV%" rmdir /s /q "%VENV%"
echo Removed virtual environment.
goto :eof
