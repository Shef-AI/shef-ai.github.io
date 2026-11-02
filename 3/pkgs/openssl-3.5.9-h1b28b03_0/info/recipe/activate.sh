if [[ "${SSL_CERT_FILE:-}" == "" ]]; then
    export SSL_CERT_FILE="${CONDA_PREFIX}/ssl/cacert.pem"
    export __CONDA_OPENSSL_CERT_FILE_SET="1"
fi
