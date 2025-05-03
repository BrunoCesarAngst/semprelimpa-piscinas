from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey, DECIMAL
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String)
    email = Column(String, unique=True)
    phone = Column(String)
    address = Column(String)
    is_admin = Column(Integer, default=0)

    appointments = relationship("Appointment", back_populates="user")

class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(DECIMAL(10,2))
    active = Column(Integer, default=1)

    appointments = relationship("Appointment", back_populates="service")

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    service_id = Column(Integer, ForeignKey('services.id'))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    status = Column(String, default='pending')
    notes = Column(Text)
    created_at = Column(String)
    address = Column(String)
    price = Column(DECIMAL(10,2))
    image_path = Column(String)

    user = relationship("User", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")

class Config(Base):
    __tablename__ = 'config'
    weekday = Column(Integer, primary_key=True)
    max_appointments = Column(Integer, default=5)

class Gallery(Base):
    __tablename__ = 'gallery'
    id = Column(Integer, primary_key=True)
    before_path = Column(String, nullable=False)   # Caminho da imagem "antes"
    after_path = Column(String, nullable=False)    # Caminho da imagem "depois"
    caption = Column(Text)                         # Legenda opcional