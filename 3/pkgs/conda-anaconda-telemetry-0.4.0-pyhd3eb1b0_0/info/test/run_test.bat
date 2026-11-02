

@echo on

pip check
IF %ERRORLEVEL% NEQ 0 exit /B 1
python -m conda --version
IF %ERRORLEVEL% NEQ 0 exit /B 1
exit /B 0
