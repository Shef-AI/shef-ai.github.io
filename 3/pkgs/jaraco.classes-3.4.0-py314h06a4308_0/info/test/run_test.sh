

set -ex



pip check
python -c "import jaraco.classes.properties as p; assert hasattr(p, 'NonDataProperty')"
pytest -v --color=yes test_jaraco_classes.py
exit 0
