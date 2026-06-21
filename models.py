from sqlalchemy import Column, ForeignKey, Integer, String, Text
from db import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)

class Reports(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    resume_text = Column(Text)
    result = Column(Text) 
   
    
                     
    
    
