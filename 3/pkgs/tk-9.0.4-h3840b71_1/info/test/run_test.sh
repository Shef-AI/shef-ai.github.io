

set -ex



test -f "${PREFIX}/bin/tclsh"
test -f "${PREFIX}/bin/wish"
test -f "${PREFIX}/bin/tclsh9.0"
test -f "${PREFIX}/bin/wish9.0"
test -f "${PREFIX}/include/tcl.h"
test -f "${PREFIX}/include/tclDecls.h"
test -f "${PREFIX}/include/tclPlatDecls.h"
test -f "${PREFIX}/include/tclPlatDecls.h"
test -f "${PREFIX}/include/tclTomMathDecls.h"
test -f "${PREFIX}/include/tclTomMath.h"
test -f "${PREFIX}/include/tk.h"
test -f "${PREFIX}/include/tkDecls.h"
test -f "${PREFIX}/include/tkPlatDecls.h"
test -f "${PREFIX}/lib/libtclstub.a"
test -f "${PREFIX}/lib/libtkstub.a"
test -f "${PREFIX}/lib/libtcl9.0.so"
test -f "${PREFIX}/lib/libtcl9tk9.0.so"
tclsh hello.tcl
tclsh9.0 hello.tcl
wish hello.tcl
wish9.0 hello.tcl
exit 0
