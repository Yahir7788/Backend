import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import get_db and MotociclistaCreate from main
from main import app, Base, Motociclista, MotociclistaSchema, MotociclistaCreate, SessionLocal, get_db

@pytest.fixture(scope="function")
def managed_test_app():
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_managed.db"  # New DB name for clarity
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocalForTest = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.drop_all(bind=engine)  # Clean start: drop tables if they exist
    Base.metadata.create_all(bind=engine)  # Create tables

    # Define the override for this specific engine and session
    def _override_get_db():
        db_session = TestingSessionLocalForTest()
        try:
            yield db_session
        finally:
            db_session.close()

    # Store original override if any, then set new one
    original_override = app.dependency_overrides.get(get_db) # Use get_db as the key
    app.dependency_overrides[get_db] = _override_get_db # Override get_db

    client = TestClient(app)

    # Provide the client and the session factory to the test
    yield client, TestingSessionLocalForTest

    # Teardown: drop tables and restore override
    Base.metadata.drop_all(bind=engine)
    if original_override:
        app.dependency_overrides[get_db] = original_override # Restore for get_db
    elif get_db in app.dependency_overrides: # Check for get_db
        del app.dependency_overrides[get_db]


def test_read_motociclista_by_id_found(managed_test_app):
    client, TestingSessionLocalForTestFunc = managed_test_app

    # Create a sample motorcyclist in the test database
    db = TestingSessionLocalForTestFunc()
    sample_motociclista_data = {
        "qr": "testqr123",
        "fecha_nacimiento": "2000-01-01",
        "numero_control": "NC12345"
    }
    db_motociclista = Motociclista(**sample_motociclista_data)
    db.add(db_motociclista)
    db.commit()
    db.refresh(db_motociclista)
    motociclista_id = db_motociclista.id
    db.close()

    # Make a GET request
    response = client.get(f"/motociclistas/{motociclista_id}")

    # Assertions
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == motociclista_id
    assert response_data["qr"] == sample_motociclista_data["qr"]
    assert response_data["fecha_nacimiento"] == sample_motociclista_data["fecha_nacimiento"]
    assert response_data["numero_control"] == sample_motociclista_data["numero_control"]

def test_read_motociclista_by_id_not_found(managed_test_app):
    client, _ = managed_test_app # We don't need the session factory here

    # Make a GET request with a non-existent ID
    non_existent_id = 999
    response = client.get(f"/motociclistas/{non_existent_id}")

    # Assertions
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


# Tests for GET /motociclistas
def test_read_motociclistas_empty(managed_test_app):
    client, _ = managed_test_app
    response = client.get("/motociclistas")
    assert response.status_code == 200
    assert response.json() == []

def test_read_motociclistas_with_data(managed_test_app):
    client, TestingSessionLocalForTestFunc = managed_test_app
    db = TestingSessionLocalForTestFunc()
    moto1_data = {"qr": "qr1", "fecha_nacimiento": "2000-01-01", "numero_control": "NC001"}
    moto2_data = {"qr": "qr2", "fecha_nacimiento": "2001-02-02", "numero_control": "NC002"}
    db.add(Motociclista(**moto1_data))
    db.add(Motociclista(**moto2_data))
    db.commit()
    db.close()

    response = client.get("/motociclistas")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    # Basic check, could be more thorough by comparing actual data
    qrs_in_response = {item["qr"] for item in response_data}
    assert moto1_data["qr"] in qrs_in_response
    assert moto2_data["qr"] in qrs_in_response

# Tests for POST /motociclistas
def test_create_motociclista_success(managed_test_app):
    client, TestingSessionLocalForTestFunc = managed_test_app
    new_moto_data = {"qr": "newqr", "fecha_nacimiento": "2002-03-03", "numero_control": "NCNEW"}

    response = client.post("/motociclistas", json=new_moto_data)
    assert response.status_code == 200 # FastAPI default for POST
    response_data = response.json()
    assert response_data["qr"] == new_moto_data["qr"]
    assert response_data["fecha_nacimiento"] == new_moto_data["fecha_nacimiento"]
    assert response_data["numero_control"] == new_moto_data["numero_control"]
    assert "id" in response_data
    motociclista_id = response_data["id"]

    # Verify in DB
    db = TestingSessionLocalForTestFunc()
    db_moto = db.query(Motociclista).filter(Motociclista.id == motociclista_id).first()
    assert db_moto is not None
    assert db_moto.qr == new_moto_data["qr"]
    db.close()

# Tests for PUT /motociclistas/{motociclista_id}
def test_update_motociclista_success(managed_test_app):
    client, TestingSessionLocalForTestFunc = managed_test_app
    db = TestingSessionLocalForTestFunc()
    original_data = {"qr": "original_qr", "fecha_nacimiento": "2003-04-04", "numero_control": "NCORIG"}
    db_moto = Motociclista(**original_data)
    db.add(db_moto)
    db.commit()
    db.refresh(db_moto)
    motociclista_id = db_moto.id
    db.close()

    updated_data_payload = {"qr": "updated_qr", "fecha_nacimiento": "2004-05-05", "numero_control": "NCUPD"}
    response = client.put(f"/motociclistas/{motociclista_id}", json=updated_data_payload)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["qr"] == updated_data_payload["qr"]
    assert response_data["fecha_nacimiento"] == updated_data_payload["fecha_nacimiento"]
    assert response_data["numero_control"] == updated_data_payload["numero_control"]
    assert response_data["id"] == motociclista_id

    # Verify in DB
    db = TestingSessionLocalForTestFunc()
    db_moto_updated = db.query(Motociclista).filter(Motociclista.id == motociclista_id).first()
    assert db_moto_updated is not None
    assert db_moto_updated.qr == updated_data_payload["qr"]
    db.close()

def test_update_motociclista_not_found(managed_test_app):
    client, _ = managed_test_app
    non_existent_id = 999
    data_payload = {"qr": "some_qr", "fecha_nacimiento": "2000-01-01", "numero_control": "NC000"}
    response = client.put(f"/motociclistas/{non_existent_id}", json=data_payload)
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}

# Tests for DELETE /motociclistas/{motociclista_id}
def test_delete_motociclista_success(managed_test_app):
    client, TestingSessionLocalForTestFunc = managed_test_app
    db = TestingSessionLocalForTestFunc()
    moto_to_delete_data = {"qr": "delete_me", "fecha_nacimiento": "2005-06-06", "numero_control": "NCDEL"}
    db_moto = Motociclista(**moto_to_delete_data)
    db.add(db_moto)
    db.commit()
    db.refresh(db_moto)
    motociclista_id = db_moto.id
    db.close()

    response = client.delete(f"/motociclistas/{motociclista_id}")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Verify in DB
    db = TestingSessionLocalForTestFunc()
    db_moto_deleted = db.query(Motociclista).filter(Motociclista.id == motociclista_id).first()
    assert db_moto_deleted is None
    db.close()

    # Optional: verify that trying to get it now returns 404
    get_response = client.get(f"/motociclistas/{motociclista_id}")
    assert get_response.status_code == 404


def test_delete_motociclista_not_found(managed_test_app):
    client, _ = managed_test_app
    non_existent_id = 999
    response = client.delete(f"/motociclistas/{non_existent_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}
