from pydantic import BaseModel
from pydantic import IPvAnyAddress
from typing import Optional


class DeviceCreate(BaseModel):

    nombre: str
    ip: str
    marca: str
    modelo: str
    version: str
    ubicacion: str
    estado: str

class DeviceUpdate(BaseModel):

    nombre: str
    ip: str
    marca: str
    modelo: str
    version: str
    ubicacion: str
    estado: str

class SyslogEventCreate(BaseModel):

    hostname: str
    facility: str
    severity: int
    mensaje: str
    source_ip: Optional[IPvAnyAddress] = None

class IncidentCreate(BaseModel):

    titulo: str
    descripcion: str
    estado: str
    responsable: str

class IncidentUpdate(BaseModel):

    estado: str
