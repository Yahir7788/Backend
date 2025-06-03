from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./motociclistas.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Motociclista(Base):
    __tablename__ = "motociclista"
    id = Column(Integer, primary_key=True, index=True)
    qr = Column(String, nullable=False)
    fecha_nacimiento = Column(String, nullable=False)
    numero_control = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

class MotociclistaSchema(BaseModel):
    id: int
    qr: str
    fecha_nacimiento: str
    numero_control: str

    class Config:
        orm_mode = True

class MotociclistaCreate(BaseModel):
    qr: str
    fecha_nacimiento: str
    numero_control: str

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/motociclistas", response_model=List[MotociclistaSchema])
def read_motociclistas():
    db = SessionLocal()
    items = db.query(Motociclista).all()
    db.close()
    return items

@app.post("/motociclistas", response_model=MotociclistaSchema)
def create_motociclista(m: MotociclistaCreate):
    db = SessionLocal()
    db_item = Motociclista(**m.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    db.close()
    return db_item

@app.put("/motociclistas/{motociclista_id}", response_model=MotociclistaSchema)
def update_motociclista(motociclista_id: int, m: MotociclistaCreate):
    db = SessionLocal()
    motociclista = db.query(Motociclista).filter(Motociclista.id == motociclista_id).first()
    if motociclista is None:
        db.close()
        raise HTTPException(status_code=404, detail="Not found")
    motociclista.qr = m.qr
    motociclista.fecha_nacimiento = m.fecha_nacimiento
    motociclista.numero_control = m.numero_control
    db.commit()
    db.refresh(motociclista)
    db.close()
    return motociclista

@app.delete("/motociclistas/{motociclista_id}")
def delete_motociclista(motociclista_id: int):
    db = SessionLocal()
    motociclista = db.query(Motociclista).filter(Motociclista.id == motociclista_id).first()
    if motociclista is None:
        db.close()
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(motociclista)
    db.commit()
    db.close()
    return {"ok": True}
