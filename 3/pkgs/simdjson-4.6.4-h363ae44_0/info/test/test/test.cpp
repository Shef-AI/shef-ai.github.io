#include <iostream>

#include <simdjson.h>

int main(int argc, const char** argv) {
  simdjson::dom::parser parser;
  simdjson::dom::element json = parser.load(argv[1]);
}
