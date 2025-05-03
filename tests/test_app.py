import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Service, Appointment, Config
from utils import hash_pwd
from datetime import date, time

# Configuração do banco de dados de teste
TEST_DB_PATH = "sqlite:///test_database.db"
engine = create_engine(TEST_DB_PATH)
Session = sessionmaker(bind=engine)

@pytest.fixture
def db_session():
    """Cria uma sessão de banco de dados para os testes"""
    Base.metadata.drop_all(engine)      # Limpa todas as tabelas
    Base.metadata.create_all(engine)    # Cria todas as tabelas
    session = Session()
    yield session
    session.rollback()
    session.close()

def test_create_user(db_session):
    """Testa a criação de um usuário"""
    user = User(
        username="testuser",
        password=hash_pwd("testpass"),
        name="Test User",
        email="test@example.com",
        phone="1234567890",
        address="Test Address"
    )
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"

def test_create_service(db_session):
    """Testa a criação de um serviço"""
    service = Service(
        name="Test Service",
        description="Test Description",
        price=100.00,
        active=1
    )
    db_session.add(service)
    db_session.commit()

    assert service.id is not None
    assert service.name == "Test Service"
    assert service.price == 100.00

def test_create_appointment(db_session):
    """Testa a criação de um agendamento"""
    # Criar usuário e serviço primeiro
    user = User(
        username="testuser",
        password=hash_pwd("testpass"),
        name="Test User"
    )
    service = Service(
        name="Test Service",
        price=100.00,
        active=1
    )
    db_session.add(user)
    db_session.add(service)
    db_session.commit()

    # Criar agendamento
    appointment = Appointment(
        user_id=user.id,
        service_id=service.id,
        date=date(2024, 1, 1),
        time=time(10, 0),
        status="novo",
        address="Test Address",
        price=100.00
    )
    db_session.add(appointment)
    db_session.commit()

    assert appointment.id is not None
    assert appointment.user_id == user.id
    assert appointment.service_id == service.id
    assert appointment.status == "novo"

def test_create_config(db_session):
    """Testa a criação de configurações"""
    for weekday in range(7):
        config = Config(
            weekday=weekday,
            max_appointments=5
        )
        db_session.add(config)
    db_session.commit()

    configs = db_session.query(Config).all()
    assert len(configs) == 7
    assert all(c.max_appointments == 5 for c in configs)