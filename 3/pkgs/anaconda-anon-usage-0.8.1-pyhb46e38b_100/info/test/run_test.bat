

@echo on

pip check
IF %ERRORLEVEL% NEQ 0 exit /B 1
anaconda-anon-usage --version
IF %ERRORLEVEL% NEQ 0 exit /B 1
anaconda-anon-usage --help
IF %ERRORLEVEL% NEQ 0 exit /B 1
conda info --json
IF %ERRORLEVEL% NEQ 0 exit /B 1
exit /B 0
