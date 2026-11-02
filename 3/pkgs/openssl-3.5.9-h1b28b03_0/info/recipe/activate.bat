@echo off
if "%SSL_CERT_FILE%"=="" (
    set SSL_CERT_FILE=%CONDA_PREFIX%\Library\ssl\cacert.pem
    set __CONDA_OPENSSL_CERT_FILE_SET="1"
)
