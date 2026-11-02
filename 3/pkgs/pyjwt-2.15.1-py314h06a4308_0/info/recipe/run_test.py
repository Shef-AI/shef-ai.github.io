import jwt

# See an example https://pyjwt.readthedocs.io/en/latest/usage.html#encoding-decoding-tokens-with-hs256
KEY = "secret"
encoded = jwt.encode({"some": "payload"}, KEY, algorithm="HS256")

assert encoded == 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzb21lIjoicGF5bG9hZCJ9.4twFt5NiznN84AWoo1d7KO1T_yoc0Z6XOpOVswacPZg'

assert jwt.decode(encoded, KEY, algorithms="HS256") == {'some': 'payload'}
