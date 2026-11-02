@echo off
if "%__CONDA_OPENSSL_CERT_FILE_SET%" == "1" (
    set SSL_CERT_FILE=
    set __CONDA_OPENSSL_CERT_FILE_SET=
)
