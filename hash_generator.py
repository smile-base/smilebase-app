import bcrypt

password = "smilepass"
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
print(hashed.decode())