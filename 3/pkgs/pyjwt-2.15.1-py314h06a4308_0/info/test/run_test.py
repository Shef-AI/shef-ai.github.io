#  tests for pyjwt-2.15.1-py314h06a4308_0 (this is a generated file);
print('===== testing package: pyjwt-2.15.1-py314h06a4308_0 =====');
print('running run_test.py');
#  --- run_test.py (begin) ---
import jwt

# See an example https://pyjwt.readthedocs.io/en/latest/usage.html#encoding-decoding-tokens-with-hs256
KEY = "secret"
encoded = jwt.encode({"some": "payload"}, KEY, algorithm="HS256")

assert encoded == 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzb21lIjoicGF5bG9hZCJ9.4twFt5NiznN84AWoo1d7KO1T_yoc0Z6XOpOVswacPZg'

assert jwt.decode(encoded, KEY, algorithms="HS256") == {'some': 'payload'}
#  --- run_test.py (end) ---

print('===== pyjwt-2.15.1-py314h06a4308_0 OK =====');
print("import: 'jwt'")
import jwt

