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
    user = get_user(username)
    if not user:
        return False
    return bcrypt.checkpw(password.encode(), user.password.encode())
