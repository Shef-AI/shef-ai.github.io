// try that conversion from absl::string_view to re2::StringPiece works

#include "absl/strings/string_view.h"
#include "re2/stringpiece.h"

absl::string_view some_function(absl::string_view text) {
  return text;
}

int main() {
   re2::StringPiece sp = "hello, world";
   // should be transformable between types by compiler
   some_function(sp);

   return 0;
}