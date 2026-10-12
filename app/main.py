from fastapi import FastAPI
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database import engine
from app.database import SessionLocal

from app.models import Base
from app.models import Device

from app.schemas import DeviceCreate

from app.schemas import DeviceUpdate

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NOC Syslog Center",
    version="0.2.0"
)

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

@app.get("/")
def inicio():
    return {
        "mensaje": "NOC Syslog Center funcionando"
    }

@app.post("/devices")
def crear_dispositivo(
    device: DeviceCreate,
    db: Session = Depends(get_db)
):

    nuevo_dispositivo = Device(
        nombre=device.nombre,
        ip=device.ip,
        marca=device.marca,
        modelo=device.modelo,
        version=device.version,
        ubicacion=device.ubicacion,
        estado=device.estado
    )

    db.add(nuevo_dispositivo)
    db.commit()
    db.refresh(nuevo_dispositivo)

    return nuevo_dispositivo

@app.get("/devices")
def listar_dispositivos(
    db: Session = Depends(get_db)
):

    dispositivos = db.query(Device).all()

    return dispositivos

@app.get("/devices/{device_id}")
def obtener_dispositivo(
    device_id: int,
    db: Session = Depends(get_db)
):

    dispositivo = db.query(Device).filter(
        Device.id == device_id
    ).first()

    if dispositivo is None:
        return {
            "error": "Dispositivo no encontrado"
        }

    return dispositivo

@app.put("/devices/{device_id}")
def actualizar_dispositivo(
    device_id: int,
    device: DeviceUpdate,
    db: Session = Depends(get_db)
):

    dispositivo = db.query(Device).filter(
        Device.id == device_id
    ).first()

    if dispositivo is None:

        return {
            "error": "Dispositivo no encontrado"
        }

    dispositivo.nombre = device.nombre
    dispositivo.ip = device.ip
    dispositivo.marca = device.marca
    dispositivo.modelo = device.modelo
    dispositivo.version = device.version
    dispositivo.ubicacion = device.ubicacion
    dispositivo.estado = device.estado

    db.commit()
    db.refresh(dispositivo)

    return dispositivo

@app.delete("/devices/{device_id}")
def eliminar_dispositivo(
    device_id: int,
    db: Session = Depends(get_db)
):

    dispositivo = db.query(Device).filter(
        Device.id == device_id
    ).first()

    if dispositivo is None:

        return {
            "error": "Dispositivo no encontrado"
        }

    db.delete(dispositivo)
    db.commit()

    return {
        "mensaje": "Dispositivo eliminado correctamente"
    }
