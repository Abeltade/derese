from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from database import engine
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)  # hashed

class Woreda(Base):
    __tablename__ = "woredas"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    kebeles = relationship("Kebele", back_populates="woreda")

class Kebele(Base):
    __tablename__ = "kebeles"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    woreda_id = Column(Integer, ForeignKey("woredas.id"))
    woreda = relationship("Woreda", back_populates="kebeles")

class Farmer(Base):
    __tablename__ = "farmers"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    woreda = Column(String)
    kebele = Column(String)
    phone = Column(String)
    registered_by = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)
