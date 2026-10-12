from pydantic import BaseModel


class DeviceCreate(BaseModel):

    nombre: str
    ip: str
    marca: str
    modelo: str
    version: str
    ubicacion: str
    estado: str