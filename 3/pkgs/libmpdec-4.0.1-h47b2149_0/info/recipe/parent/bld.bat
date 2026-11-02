@ECHO off

set dbg=0

REM Detect target architecture - ARM64 needs ansi64 (pure C, no x64 MASM assembly)
REM Check target_platform first (conda-build), then fall back to processor arch
if "%target_platform%"=="win-arm64" (
    set machine=ansi64
) else (
    set machine=x64
)

mkdir %LIBRARY_BIN%
mkdir %LIBRARY_LIB%
mkdir %LIBRARY_INC%

cd libmpdec
copy /y Makefile.vc Makefile
nmake clean
nmake MACHINE=%machine% DEBUG=%dbg%

REM copy /y "libmpdec-4.lib" %LIBRARY_LIB%
copy /y "libmpdec-4.dll" %LIBRARY_BIN%
copy /y "libmpdec-4.dll.lib" "%LIBRARY_LIB%\mpdec.lib"
REM copy /y "libmpdec-4.dll.exp" %LIBRARY_LIB%
copy /y "mpdecimal.h" %LIBRARY_INC%

cd ..\libmpdec++
copy /y Makefile.vc Makefile
nmake clean
nmake DEBUG=%dbg%

REM copy /y "libmpdec++-4.lib" %LIBRARY_LIB%
copy /y "libmpdec++-4.dll" %LIBRARY_BIN%
copy /y "libmpdec++-4.dll.lib" "%LIBRARY_LIB%\mpdec++.lib"
REM copy /y "libmpdec-4.dll.exp" %LIBRARY_LIB%
copy /y "decimal.hh" %LIBRARY_INC%
