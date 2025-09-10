import streamlit_authenticator as stauth

hashed_pw = stauth.Hasher(['smilebase2025zdrewqaz']).generate()
print(hashed_pw)
