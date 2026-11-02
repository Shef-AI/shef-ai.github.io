import os
import signal
import subprocess
import sys
import time

# this test assumes it is being run in examples/python/helloworld,
# after having generated the helloworld_pb2{,_grpc} modules (see meta.yaml)
import grpc
import helloworld_pb2
import helloworld_pb2_grpc


# start server (and wait a little)
print('Starting server...')
pid = subprocess.Popen([sys.executable, "greeter_server.py"]).pid
time.sleep(5)

# run this a couple times because it happens randomly, see
# https://github.com/conda-forge/grpc-cpp-feedstock/issues/281
print('Running client...')
for _ in range(1000):
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = helloworld_pb2_grpc.GreeterStub(channel)
        response = stub.SayHello(helloworld_pb2.HelloRequest(name='you'))

# tear down server
print('Terminating server...')
os.kill(pid, signal.SIGTERM)

print('Success!')
