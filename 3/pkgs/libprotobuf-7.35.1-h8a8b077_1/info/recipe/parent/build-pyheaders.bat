@echo on

robocopy python/ %LIBRARY_PREFIX%\include *.h /E
if %ERRORLEVEL% GEQ 8 exit 1

