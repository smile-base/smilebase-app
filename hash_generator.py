from streamlit_authenticator.utilities.hasher import Hasher

hashed_pw = Hasher().hash('smilebase2025zdrewqaz')
print(hashed_pw)