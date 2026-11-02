@echo on

if [%PKG_NAME%] == [re2] (
    REM everything else but the DLL
    cmake --install build
    if %ERRORLEVEL% neq 0 exit 1
) else (
    REM package only the DLL for the output libre2-{{soversion}};
    REM sorted second because it keeps changing names, easier in "else"
    copy build\re2.dll %LIBRARY_BIN%
)
