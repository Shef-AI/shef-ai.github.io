load("@rules_python//python:defs.bzl", "py_runtime", "py_runtime_pair")

py_runtime(
    name = "python3",
    python_version = "PY3",
    interpreter_path = '@@SRC_DIR@@/python.shebang',
    stub_shebang = '#!@@SRC_DIR@@/python.shebang',
)

py_runtime_pair(
    name = "py_runtime_pair",
    py3_runtime = ":python3",
)

toolchain(
    name = "py_toolchain",
    toolchain = ":py_runtime_pair",
    toolchain_type = "@rules_python//python:toolchain_type",
)
