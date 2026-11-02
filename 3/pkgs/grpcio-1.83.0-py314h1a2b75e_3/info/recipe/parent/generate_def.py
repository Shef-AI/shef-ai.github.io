import glob
import os
import sys

symbols_dir = sys.argv[1]  # symbols/
output_file = sys.argv[2]  # grpc.def

# output of dumpbin for objects looks something like:
# ```
# Microsoft (R) COFF/PE Dumper Version 14.42.34436.0
# Copyright (C) Microsoft Corporation.  All rights reserved.
#
# Dump of file msg.obj
#
# File Type: EXTENDED COFF OBJECT
#
# COFF SYMBOL TABLE
# 000 010475CE ABS    notype       Static       | @comp.id
# 001 80010190 ABS    notype       Static       | @feat.00
# 002 00000002 ABS    notype       Static       | @vol.md
# 003 00000000 SECT1  notype       Static       | .drectve
#     Section length   2F, #relocs    0, #linenums    0, checksum        0
# 005 00000000 SECT2  notype       Static       | .debug$S
#     Section length   BC, #relocs    0, #linenums    0, checksum        0
# 007 00000000 SECT3  notype       Static       | .rdata
#     Section length   6A, #relocs    0, #linenums    0, checksum 52734268
# 009 00000000 SECT3  notype       Static       | ?c_type@?1??upb_FieldType_CType@@9@9 (`upb_FieldType_CType'::`2'::c_type)
# 00A 00000048 SECT3  notype       Static       | ?size@?1??_upb_CType_SizeLg2_dont_copy_me__upb_internal_use_only@@9@9 (`_upb_CType_SizeLg2_dont_copy_me__upb_internal_use_only'::`2'::size)
# [...]
# 07F 00000000 SECT34 notype ()    Static       | upb_MiniTable_FieldCount
# 080 00000000 SECT35 notype ()    Static       | upb_MiniTable_GetFieldByIndex
# 081 00000000 UNDEF  notype ()    External     | upb_Map_New
# 082 00000000 UNDEF  notype ()    External     | upb_Map_Size
# 083 00000000 UNDEF  notype ()    External     | upb_Map_Next
# [...]
# String Table Size = 0x13F5 bytes
#
#   Summary
#
#          398 .chks64
#           BC .debug$S
#           2F .drectve
#          168 .pdata
#           6A .rdata
#         132C .text$mn
#          1E4 .xdata
# ```

symbols = set()
for txt_file in glob.glob(os.path.join(symbols_dir, "symbols_*.txt")):
    with open(txt_file, "r") as f:
        for line in f:
            # we only want symbols (filter to lines with "|")
            if "|" not in line:
                continue
            # filter out UNDEF symbols that are not present in the object,
            # i.e. supposed to come from another library (it could also be
            # from another object, but since we do a union, it doesn't matter);
            # Static symbols aren't visible to the linker, so even if we put
            # them in the .def file, they would not be found; save the hassle.
            if "UNDEF" in line or "Static" in line:
                continue
            # get pure symbol, i.e. what comes after "|", minus spaces, and removing potentially
            # trailing demangled names (e.g. "(`upb_FieldType_CType'::`2'::c_type)" above);
            # don't use [-1] because some demangled symbols contain `operator|`
            symbol = line.split("|")[1].strip().split()[0]
            # keep constructors/destructors before filtering other symbols starting with "??"
            if any(symbol.startswith(x) for x in ["??0", "??1"]):
                symbols.add(symbol)
                continue
            # skip labels and metadata
            if "Label" in line or any(symbol.startswith(x) for x in [".", "$", "@", "??", "?$", "__"]):
                continue
            # skip opencensus for now; re-evaluate together with #220
            if "opencensus" in symbol.lower():
                continue
            symbols.add(symbol)
            ### potential further avenues for symbol reduction
            # # Skip lambda-related symbols and anonymous namespaces
            # if any(x in symbol for x in ["<lambda_", "?A0x"]):
            #    continue
            # # Skip static pdata/dtors/initializers tied to functions
            # if any(x in line for x in ["$pdata$", "$dtor$", "$initializer$"]):
            #    continue

out_lines = ["EXPORTS"] + [f"    {x}" for x in sorted(list(symbols))] + [""]

with open(output_file, "w") as def_file:
    def_file.write("\n".join(out_lines))
