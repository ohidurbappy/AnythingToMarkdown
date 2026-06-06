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
REM    make app             build the clickable Windows app (dist\AnythingToMarkdown)
REM    make open-app        open the built app folder
REM    make icon            regenerate the app icons
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
echo   app         Build the clickable Windows app (dist\%APP_NAME%)
echo   open-app    Open the built app folder
echo   icon        Regenerate the app icons
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
echo Built: dist\%APP_NAME%\%APP_NAME%.exe
echo Run it by double-clicking %APP_NAME%.exe, or: make open-app
goto :eof

REM ---------------------------------------------------------------------------
:open_app
if exist "%ROOT%dist\%APP_NAME%" (
    explorer "%ROOT%dist\%APP_NAME%"
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
