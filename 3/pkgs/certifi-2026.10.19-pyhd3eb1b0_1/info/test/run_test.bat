

@echo on

pip check
IF %ERRORLEVEL% NEQ 0 exit /B 1
python -c "from importlib.metadata import version; assert(version('certifi')=='2026.10.19')"
IF %ERRORLEVEL% NEQ 0 exit /B 1
pytest -vv certifi/certifi/tests
IF %ERRORLEVEL% NEQ 0 exit /B 1
exit /B 0
