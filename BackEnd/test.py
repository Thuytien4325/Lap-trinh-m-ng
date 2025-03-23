import bcrypt

hashed = bcrypt.hashpw(b"test", bcrypt.gensalt())
print(hashed)
