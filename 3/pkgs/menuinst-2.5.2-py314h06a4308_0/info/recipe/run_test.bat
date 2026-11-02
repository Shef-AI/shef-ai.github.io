@ECHO ON

:: Pip check
"%PYTHON%" -m pip check
IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

:: Create a .nonadmin file so that the menuinst tests
:: do not try to run with admin privileges
echo. > "%PREFIX%\.nonadmin"
IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

:: PBP runs conda-build under a separate "tst" prefix; CONDA_EXE may still
:: point at that broken tooling conda. Point menuinst at the test env's conda.
set "CONDA_EXE=%CONDA_PREFIX%\Scripts\conda.exe"
if not exist "%CONDA_EXE%" set "CONDA_EXE=%CONDA_PREFIX%\conda.exe"
set "CONDA_ROOT_PREFIX=%CONDA_PREFIX%"

echo Running tests for Python %PYTHON_VERSION%
:: Cannot run tests in test_schema.py because hypothesis-jsonschema is not on defaults
:: Cannot run others because privilege elevation is not possible on the build platform
pytest tests\ -vvv --ignore=tests\test_schema.py --ignore=tests\test_elevation.py -k "not test_create_and_remove_shortcut and not test_package_1_windows"
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
