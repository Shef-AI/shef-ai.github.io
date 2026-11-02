

set -ex



python -c "from google.protobuf.internal import api_implementation; print(api_implementation.Type())"
python -c "from google.protobuf.internal import api_implementation; assert api_implementation.Type() == 'upb'"
pip check
exit 0
