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

from app.models import Incident
from app.schemas import IncidentCreate

from app.schemas import IncidentUpdate

from datetime import datetime

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

@app.post("/incidents")
def crear_incidente(
    incidente: IncidentCreate,
    db: Session = Depends(get_db)
):

    nuevo_incidente = Incident(

        titulo=incidente.titulo,
        descripcion=incidente.descripcion,
        estado=incidente.estado,
        responsable=incidente.responsable

    )

    db.add(nuevo_incidente)

    db.commit()

    db.refresh(nuevo_incidente)

    return nuevo_incidente

@app.get("/incidents")
def listar_incidentes(
    db: Session = Depends(get_db)
):

    incidentes = db.query(
        Incident
    ).all()

    return incidentes

@app.get("/dashboard/incidents")
def resumen_incidentes(
    db: Session = Depends(get_db)
):

    total = db.query(Incident).count()

    abiertos = db.query(Incident).filter(
        Incident.estado == "Abierto"
    ).count()

    cerrados = db.query(Incident).filter(
        Incident.estado == "Cerrado"
    ).count()

    return {
        "total_incidentes": total,
        "abiertos": abiertos,
        "cerrados": cerrados
    }

@app.put("/incidents/{incident_id}")
def actualizar_incidente(
    incident_id: int,
    incidente: IncidentUpdate,
    db: Session = Depends(get_db)
):

    incidente_db = db.query(
        Incident
    ).filter(
        Incident.id == incident_id
    ).first()

    if incidente_db is None:

        return {
            "error": "Incidente no encontrado"
        }

    incidente_db.estado = incidente.estado

    if incidente.estado == "Cerrado":

        incidente_db.fecha_cierre = datetime.utcnow()

    db.commit()

    db.refresh(
        incidente_db
    )

    return incidente_db

@app.get("/dashboard/incidents")
def resumen_incidentes(
    db: Session = Depends(get_db)
):

    total = db.query(Incident).count()

    abiertos = db.query(Incident).filter(
        Incident.estado == "Abierto"
    ).count()

    cerrados = db.query(Incident).filter(
        Incident.estado == "Cerrado"
    ).count()

    return {
        "total_incidentes": total,
        "abiertos": abiertos,
        "cerrados": cerrados
    }

@app.get("/generator/syslog/{vendor}/{ip}")
def generar_syslog(
    vendor: str,
    ip: str
):
    vendor = vendor.lower()
    if vendor == "cisco":

        return {
            "vendor": "Cisco",
            "config": f"""
logging host {ip}
logging trap informational
"""
        }
    elif vendor == "fortinet":

        return {
            "vendor": "Fortinet",
            "config": f"""
config log syslogd setting
set status enable
set server "{ip}"
end
"""
        }
    elif vendor == "huawei":

        return {
            "vendor": "Huawei",
            "config": f"""
info-center loghost {ip}
info-center enable
"""
        }
    else:

        return {
            "error": "Fabricante no soportado"
        }    
    
@app.get("/dashboard/incidents/list")
def listar_incidentes_dashboard(
    db: Session = Depends(get_db)
):

    return db.query(
        Incident
    ).all()

@app.get("/health")
def health():

    return {
        "status": "UP",
        "database": "UP",
        "api": "UP"
    }