

set -ex



pip check
pygmentize -h
pytest -v tests  --ignore=tests/contrast/test_contrasts.py  --deselect=tests/test_basic_api.py::test_lexer_classes
exit 0
