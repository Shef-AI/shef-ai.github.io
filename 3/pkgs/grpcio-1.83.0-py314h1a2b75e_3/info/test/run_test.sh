

set -ex



python -m pip check
python -c "from pathlib import Path; import grpc; p = Path(grpc.__file__).resolve().parent / '_cython' / '_credentials' / 'roots.pem'; assert 'emSign ECC Root CA - G3' not in p.read_text(), p"
python -c "from pathlib import Path; import grpc; p = Path(grpc.__file__).resolve().parent / '_cython' / '_credentials' / 'roots.pem'; assert 'emSign Root CA - G1' not in p.read_text(), p"
python grpcio_distribtest.py
cd examples/python/helloworld
python -m grpc_tools.protoc -I../../protos --python_out=. --pyi_out=. --grpc_python_out=. ../../protos/helloworld.proto
cp ../../../test_grpcio_helloworld.py .
python test_grpcio_helloworld.py
exit 0
