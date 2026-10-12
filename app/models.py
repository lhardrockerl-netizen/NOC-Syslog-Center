from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime

from datetime import datetime

from .database import Base


class Device(Base):

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    nombre = Column(String)
    ip = Column(String)

    marca = Column(String)
    modelo = Column(String)
    version = Column(String)

    ubicacion = Column(String)
    estado = Column(String)

    fecha_actualizacion = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )