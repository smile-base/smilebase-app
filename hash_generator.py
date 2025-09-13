import bcrypt

password = "smilebase2025zdrewqaz"
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
print(hashed.decode())