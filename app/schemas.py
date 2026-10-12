from pydantic import BaseModel


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