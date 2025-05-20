from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey, DECIMAL, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import secrets

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False)

    appointments = relationship("Appointment", back_populates="user")
    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', name='{self.name}', is_admin={self.is_admin})>"

    def generate_auth_token(self):
        """Gera um novo token de autenticação para o usuário"""
        from streamlit_app import generate_token, create_secure_cookie

        # Gerar token
        token = generate_token()

        # Criar cookie seguro
        cookie_value = create_secure_cookie(self.id, token)

        # Salvar token no banco
        from sqlalchemy.orm import Session
        from streamlit_app import Session as DBSession

        session = DBSession()
        try:
            from streamlit_app import AuthToken
            auth_token = AuthToken(
                user_id=self.id,
                token=token,
                created_at=datetime.now().isoformat(),
                expires_at=(datetime.now() + timedelta(hours=10)).isoformat()
            )
            session.add(auth_token)
            session.commit()
            return cookie_value
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def validate_token(self, token):
        """Valida um token de autenticação"""
        from sqlalchemy.orm import Session
        from streamlit_app import Session as DBSession, decode_secure_cookie

        try:
            # Decodificar cookie
            user_id = decode_secure_cookie(token)
            if user_id != self.id:
                return False

            # Verificar token no banco
            session = DBSession()
            try:
                from streamlit_app import AuthToken
                from datetime import datetime

                auth_token = session.query(AuthToken).filter_by(
                    user_id=self.id,
                    token=token
                ).first()

                if not auth_token:
                    return False

                # Verificar expiração
                expires_at = datetime.fromisoformat(auth_token.expires_at)
                if datetime.now() > expires_at:
                    session.delete(auth_token)
                    session.commit()
                    return False

                return True
            finally:
                session.close()
        except Exception:
            return False

    def delete_token(self, token):
        """Remove um token de autenticação"""
        from sqlalchemy.orm import Session
        from streamlit_app import Session as DBSession

        session = DBSession()
        try:
            from streamlit_app import AuthToken
            auth_token = session.query(AuthToken).filter_by(
                user_id=self.id,
                token=token
            ).first()

            if auth_token:
                session.delete(auth_token)
                session.commit()
        finally:
            session.close()

class AuthToken(Base):
    __tablename__ = 'auth_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String(64), unique=True, nullable=False)
    created_at = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)

    user = relationship("User", back_populates="tokens")

    def __repr__(self):
        return f"<AuthToken(user_id={self.user_id}, token='{self.token[:8]}...')>"

    @property
    def is_expired(self):
        """Verifica se o token está expirado"""
        from datetime import datetime
        return datetime.now() > datetime.fromisoformat(self.expires_at)

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