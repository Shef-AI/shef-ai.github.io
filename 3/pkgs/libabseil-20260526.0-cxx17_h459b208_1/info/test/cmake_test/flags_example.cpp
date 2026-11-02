// taken from https://abseil.io/docs/cpp/guides/flags
// exercises both flags and non-flags (for abseil_dll) import

#include <iostream>
#include <string>

#include "absl/flags/flag.h"
#include "absl/flags/marshalling.h"
#include "absl/strings/string_view.h"

struct PortNumber {
  explicit PortNumber(int p = 0) : port(p) {}

  int port;  // Valid range is [0..32767]
};

// Returns a textual flag value corresponding to the PortNumber `p`.
std::string AbslUnparseFlag(PortNumber p) {
  // Delegate to the usual unparsing for int.
  return absl::UnparseFlag(p.port);
}

// Parses a PortNumber from the command line flag value `text`.
// Returns true and sets `*p` on success; returns false and sets `*error`
// on failure.
bool AbslParseFlag(absl::string_view text, PortNumber* p, std::string* error) {
  // Convert from text to int using the int-flag parser.
  if (!absl::ParseFlag(text, &p->port, error)) {
    return false;
  }
  if (p->port < 0 || p->port > 32767) {
    *error = "not in range [0,32767]";
    return false;
  }
  return true;
}

ABSL_FLAG(PortNumber, port, PortNumber(0), "What port to listen on");

// exercise above code

int main() {
   PortNumber p = absl::GetFlag(FLAGS_port);
   std::cout << "default: " << p.port << std::endl;

   absl::SetFlag(&FLAGS_port, 10101);
   p = absl::GetFlag(FLAGS_port);
   std::cout << "modified: " << p.port << std::endl;

   return 0;
}
