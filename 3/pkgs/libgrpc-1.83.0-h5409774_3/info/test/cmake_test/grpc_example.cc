// inspired by usage in arrow, see
// https://github.com/apache/arrow/blob/apache-arrow-12.0.0/cpp/src/arrow/flight/transport/grpc/grpc_client.cc#L620-L622

#include <memory>

#include <grpcpp/security/tls_credentials_options.h>

constexpr char kDummyRootCert[] =
    "-----BEGIN CERTIFICATE-----\n"
    "[snip]\n"
    "-----END CERTIFICATE-----\n";

int main()
{
    auto certificate_provider = std::make_shared<::grpc::experimental::StaticDataCertificateProvider>(
          kDummyRootCert);
    return 0;
}
