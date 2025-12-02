import streamlit as st
from database import SessionLocal
from models import User, create_tables
import bcrypt

create_tables() 

def get_user(username):
    db = SessionLocal()
    return db.query(User).filter(User.username == username).first()

def register_user(username, password):
    db = SessionLocal()
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_user = User(username=username, password=hashed)
    db.add(new_user)
    db.commit()

def login_user(username, password):
    print(f"Attempting login for user: {username}")
    print(f"Password received: '{password}'")
    print(f"Repr of password: {repr(password)}")
    user = get_user(username)
    if not user:
        print("User not found.")
        return False
    
    print(f"User found. Stored hash: {user.password}")
    password_match = bcrypt.checkpw(password.encode(), user.password.encode())
    print(f"Password match result: {password_match}")
    
    return password_match
