@echo off
SETLOCAL EnableDelayedExpansion

for /f "tokens=1 delims=." %%a in ("%PKG_VERSION%") do set "ICU_MAJOR=%%a"

if "%target_platform%"=="win-arm64" (
    set "PLATFORM=ARM64"
    set "BINDIR=binARM64"
    set "LIBDIR=libARM64"
) else if "%ARCH%"=="64" (
    set "PLATFORM=x64"
    set "BINDIR=bin64"
    set "LIBDIR=lib64"
) else (
    set "PLATFORM=Win32"
    set "BINDIR=bin"
    set "LIBDIR=lib"
)

if not exist "source\data\out\tmp" mkdir "source\data\out\tmp"

:: Build the data stub first so we can ship the small icudt.dll alias after
:: makedata overwrites icudt%ICU_MAJOR%.dll with the full data library.
set "ICUDT_STUB=%CD%\icudt_stub.dll"
msbuild source\stubdata\stubdata.vcxproj ^
    /p:Configuration=Release ^
    /p:Platform=%PLATFORM% ^
    /p:WindowsTargetPlatformVersion=%WindowsSDKVer%
if errorlevel 1 exit 1
if not exist "%BINDIR%\icudt%ICU_MAJOR%.dll" (
    echo ERROR: ICU stubdata build failed - icudt%ICU_MAJOR%.dll not found in %BINDIR%.
    exit 1
)
copy /Y "%BINDIR%\icudt%ICU_MAJOR%.dll" "%ICUDT_STUB%"
if errorlevel 1 exit 1

msbuild source\allinone\allinone.sln ^
    /p:Configuration=Release ^
    /p:Platform=%PLATFORM% ^
    /p:WindowsTargetPlatformVersion=%WindowsSDKVer% ^
    /p:SkipUWP=true

:: msbuild may return non-zero due to test data build needing the py launcher.
:: Verify the essential artifacts exist instead.
if not exist "%BINDIR%\icuuc*.dll" (
    echo ERROR: ICU build failed - essential DLLs not found in %BINDIR%.
    if not exist "%BINDIR%" (
        echo Listing top-level directories for debugging:
        dir /ad /b
    ) else (
        echo Contents of %BINDIR%:
        dir /b "%BINDIR%"
    )
    exit 1
)
if not exist "%BINDIR%\icudt*.dll" (
    echo ERROR: ICU data build failed - icudt*.dll not found in %BINDIR%.
    exit 1
)
if not exist "%BINDIR%\icutest%ICU_MAJOR%.dll" (
    echo ERROR: ICU build failed - icutest%ICU_MAJOR%.dll not found in %BINDIR%.
    exit 1
)

:: Install headers
if not exist "%LIBRARY_INC%\unicode" mkdir "%LIBRARY_INC%\unicode"
xcopy /Y "source\common\unicode\*.h" "%LIBRARY_INC%\unicode\"
if errorlevel 1 exit 1
xcopy /Y "source\i18n\unicode\*.h" "%LIBRARY_INC%\unicode\"
if errorlevel 1 exit 1
xcopy /Y "source\io\unicode\*.h" "%LIBRARY_INC%\unicode\"
if errorlevel 1 exit 1

:: Install import libraries
copy /Y "%LIBDIR%\icu*.lib" "%LIBRARY_LIB%\"
if errorlevel 1 exit 1

:: Install versioned DLLs
copy /Y "%BINDIR%\icu*.dll" "%LIBRARY_BIN%\"
if errorlevel 1 exit 1

:: Install unversioned DLL aliases expected by existing consumers
for %%s in (uc in io tu test) do (
    copy /Y "%LIBRARY_BIN%\icu%%s%ICU_MAJOR%.dll" "%LIBRARY_BIN%\icu%%s.dll"
    if errorlevel 1 exit 1
)
copy /Y "%ICUDT_STUB%" "%LIBRARY_BIN%\icudt.dll"
if errorlevel 1 exit 1
del /F /Q "%ICUDT_STUB%"

:: Install command-line tools
for %%t in (derb genbrk genccode gencfu gencmn gencnval gendict gennorm2 genrb gensprep icuexportdata icuinfo icupkg makeconv pkgdata uconv) do (
    if exist "%BINDIR%\%%t.exe" copy /Y "%BINDIR%\%%t.exe" "%LIBRARY_BIN%\"
)

:: Install pkg-config files
if not exist "%LIBRARY_LIB%\pkgconfig" mkdir "%LIBRARY_LIB%\pkgconfig"

> "%LIBRARY_LIB%\pkgconfig\icu-uc.pc" (
    echo prefix=${pcfiledir}/../..
    echo exec_prefix=${prefix}
    echo libdir=${exec_prefix}/lib
    echo includedir=${prefix}/include
    echo.
    echo Name: icu-uc
    echo Description: International Components for Unicode: Common Library
    echo Version: %PKG_VERSION%
    echo Libs: -L${libdir} -licuuc -licudt
    echo Cflags: -I${includedir}
)

> "%LIBRARY_LIB%\pkgconfig\icu-i18n.pc" (
    echo prefix=${pcfiledir}/../..
    echo exec_prefix=${prefix}
    echo libdir=${exec_prefix}/lib
    echo includedir=${prefix}/include
    echo.
    echo Name: icu-i18n
    echo Description: International Components for Unicode: Internationalization Library
    echo Version: %PKG_VERSION%
    echo Requires: icu-uc
    echo Requires.private: icu-uc
    echo Libs: -L${libdir} -licuin
    echo Cflags: -I${includedir}
)

> "%LIBRARY_LIB%\pkgconfig\icu-io.pc" (
    echo prefix=${pcfiledir}/../..
    echo exec_prefix=${prefix}
    echo libdir=${exec_prefix}/lib
    echo includedir=${prefix}/include
    echo.
    echo Name: icu-io
    echo Description: International Components for Unicode: Stream and I/O Library
    echo Version: %PKG_VERSION%
    echo Requires: icu-uc icu-i18n
    echo Requires.private: icu-i18n
    echo Libs: -L${libdir} -licuio
    echo Cflags: -I${includedir}
)
