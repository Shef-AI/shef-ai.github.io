if "%ARCH%"=="32" (
   set MACHINE="IX86"
   :: A different SDK is needed when build with VS 2017 and 2015
   :: http://wiki.tcl.tk/54819
   if "%VS_MAJOR%"=="14" (
    echo "Switching SDK versions"
    call "%VS140COMNTOOLS%..\..\VC\vcvarsall.bat" x86 10.0.15063.0
   )
) else if "%target_platform%"=="win-arm64" (
  set MACHINE="ARM64"
) else (
  set MACHINE="AMD64"
  :: A different SDK is needed when build with VS 2017 and 2015
  :: http://wiki.tcl.tk/54819
  if "%VS_MAJOR%"=="14" (
    echo "Switching SDK versions"
    call "%VS140COMNTOOLS%..\..\VC\vcvarsall.bat" x64 10.0.15063.0
  )
)

pushd tcl%PKG_VERSION%\win
nmake nmakehlp.exe
nmake -f makefile.vc INSTALLDIR=%LIBRARY_PREFIX% MACHINE=%MACHINE% OPTS=noembed release
if %ERRORLEVEL% GTR 0 exit 1
nmake -f makefile.vc INSTALLDIR=%LIBRARY_PREFIX% MACHINE=%MACHINE% OPTS=noembed install
if %ERRORLEVEL% GTR 0 exit 1
popd

REM Required for having tmschema.h accessible.  Newer VS versions do not include this.
REM If you don't have this path, you are missing the Windows 7 SDK.  Please install this.
REM   NOTE: Later SDKs remove tmschema.h.  It really is necessary to use the Win 7 SDK.
set INCLUDE=%INCLUDE%;c:\Program Files (x86)\Microsoft SDKs\Windows\v7.1A\Include

:: Tk build

pushd tk%PKG_VERSION%\win
nmake nmakehlp.exe
nmake -f makefile.vc INSTALLDIR=%LIBRARY_PREFIX% MACHINE=%MACHINE% TCLDIR=..\..\tcl%PKG_VERSION% OPTS=noembed release
if %ERRORLEVEL% GTR 0 exit 1
nmake -f makefile.vc INSTALLDIR=%LIBRARY_PREFIX% MACHINE=%MACHINE% TCLDIR=..\..\tcl%PKG_VERSION% OPTS=noembed install
if %ERRORLEVEL% GTR 0 exit 1

REM NB Tcl >=9.0 no longer uses the t for threading suffix:
REM https://github.com/tcltk/tcl/blob/main/win/rules.vc#L1057

:: Make sure that `wish` can be called without the version info.
copy %LIBRARY_PREFIX%\bin\wish%VER_SUFFIX%.exe %LIBRARY_PREFIX%\bin\wish.exe
copy %LIBRARY_PREFIX%\bin\tclsh%VER_SUFFIX%.exe %LIBRARY_PREFIX%\bin\tclsh.exe

popd
