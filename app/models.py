from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime

from datetime import datetime

from .database import Base

from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

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

class SyslogEvent(Base):

    __tablename__ = "syslog_events"

    id = Column(Integer, primary_key=True, index=True)

    hostname = Column(String)
    facility = Column(String)

    severity = Column(Integer)

    mensaje = Column(String)

    fecha = Column(
        DateTime,
        default=datetime.utcnow
    )

class Incident(Base):

    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    titulo = Column(String)

    descripcion = Column(String)

    estado = Column(String)

    responsable = Column(String)

    fecha_creacion = Column(
        DateTime,
        default=datetime.utcnow
    )

    fecha_cierre = Column(
        DateTime,
        nullable=True
    )