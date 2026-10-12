from fastapi import FastAPI
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database import engine
from app.database import SessionLocal

from app.models import Base
from app.models import Device

from app.schemas import DeviceCreate

from app.schemas import DeviceUpdate

from app.schemas import SyslogEventCreate
from app.models import SyslogEvent

from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NOC Syslog Center",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

def obtener_nombre_severidad(severity):

    severidades = {
        0: "Emergency",
        1: "Alert",
        2: "Critical",
        3: "Error",
        4: "Warning",
        5: "Notice",
        6: "Informational",
        7: "Debug"
    }

    return severidades.get(
        severity,
        "Desconocida"
    )

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

@app.post("/syslog")
def crear_evento_syslog(
    evento: SyslogEventCreate,
    db: Session = Depends(get_db)
):

    nuevo_evento = SyslogEvent(
        hostname=evento.hostname,
        facility=evento.facility,
        severity=evento.severity,
        mensaje=evento.mensaje
    )

    db.add(nuevo_evento)
    db.commit()
    db.refresh(nuevo_evento)

    return nuevo_evento

@app.get("/syslog")
def listar_eventos_syslog(
    db: Session = Depends(get_db)
):

    eventos = db.query(SyslogEvent).all()

    return eventos

@app.get("/syslog/clasificados")
def listar_syslog_clasificados(
    db: Session = Depends(get_db)
):

    eventos = db.query(SyslogEvent).all()

    resultado = []

    for evento in eventos:

        resultado.append({
            "id": evento.id,
            "hostname": evento.hostname,
            "facility": evento.facility,
            "severity": evento.severity,
            "nivel": obtener_nombre_severidad(
                evento.severity
            ),
            "mensaje": evento.mensaje,
            "fecha": evento.fecha
        })

    return resultado

@app.get("/syslog/severity/{nivel}")
def filtrar_por_severidad(
    nivel: int,
    db: Session = Depends(get_db)
):

    eventos = db.query(SyslogEvent).filter(
        SyslogEvent.severity == nivel
    ).all()

    return eventos

@app.get("/syslog/hostname/{hostname}")
def filtrar_por_hostname(
    hostname: str,
    db: Session = Depends(get_db)
):

    eventos = db.query(SyslogEvent).filter(
        SyslogEvent.hostname == hostname
    ).all()

    return eventos

@app.get("/dashboard/resumen")
def resumen_dashboard(
    db: Session = Depends(get_db)
):

    total = db.query(SyslogEvent).count()

    criticos = db.query(SyslogEvent).filter(
        SyslogEvent.severity <= 2
    ).count()

    errores = db.query(SyslogEvent).filter(
        SyslogEvent.severity == 3
    ).count()

    advertencias = db.query(SyslogEvent).filter(
        SyslogEvent.severity == 4
    ).count()

    informativos = db.query(SyslogEvent).filter(
        SyslogEvent.severity >= 5
    ).count()

    return {
        "total_eventos": total,
        "criticos": criticos,
        "errores": errores,
        "advertencias": advertencias,
        "informativos": informativos
    }