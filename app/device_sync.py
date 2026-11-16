"""Actualiza nombres de inventario por el devid estable de FortiGate."""
import re
import os
import ipaddress
from datetime import datetime

from app.models import Device, DeviceIdentity, SyslogEvent


def source_is_authorized(source_ip):
    try:
        address = ipaddress.ip_address(source_ip)
        networks = os.environ.get("NOC_AUTOREGISTER_NETWORKS", "192.168.125.0/24")
        return any(address in ipaddress.ip_network(item.strip()) for item in networks.split(",") if item.strip())
    except ValueError:
        return False


def register_syslog_device(db, event):
    source = str(event.source_ip) if event.source_ip else None
    if not source:
        return sync_device_name(db, event.mensaje)
    if not source_is_authorized(source):
        return None
    fields = fortigate_fields(event.mensaje)
    serial = fields.get("devid") if fields.get("devid", "").startswith("FG") else None
    hostname = fields.get("devname") or event.hostname or source
    identity = db.get(DeviceIdentity, serial) if serial else None
    device = db.get(Device, identity.device_id) if identity else None
    if device and db.query(Device).filter(Device.ip == source, Device.id != device.id).first():
        return None  # La IP nueva ya corresponde a otro registro.
    if identity and device is None:
        db.delete(identity)
        db.flush()
    if device is None:
        by_ip = db.query(Device).filter(Device.ip == source).all()
        if len(by_ip) > 1:
            return None  # Inventario ambiguo: no escoger un equipo arbitrariamente.
        if by_ip:
            device = by_ip[0]
            assigned = db.query(DeviceIdentity).filter(DeviceIdentity.device_id == device.id).first()
            if assigned and assigned.serial != serial:
                return None  # No renombrar un equipo con identidad distinta por reutilizar su IP.
        elif serial:
            device = sync_device_name(db, event.mensaje)
    brand = "Por identificar"
    if serial:
        brand = "Fortinet"
    elif "MIKROTIK" in hostname.upper():
        brand = "MikroTik"
    elif re.search(r"%(?:LINK|LINEPROTO|SYS|SEC_LOGIN|OSPF|BGP)-\d-[A-Z_]+", event.mensaje):
        brand = "Cisco"
    if device is None:
        device = Device(nombre=hostname, ip=source, marca=brand, modelo="Por confirmar",
                        version="Por confirmar", ubicacion="Descubierto por syslog", estado="Reportando")
        db.add(device)
        db.flush()
    else:
        device.nombre = hostname
        device.ip = source
        if device.marca in (None, "", "Por identificar"):
            device.marca = brand
        device.estado = "Reportando"
    if serial and db.get(DeviceIdentity, serial) is None:
        # Una sesion puede tener una identidad pendiente de flush del metodo anterior.
        db.flush()
        if db.get(DeviceIdentity, serial) is None:
            db.add(DeviceIdentity(serial=serial, device_id=device.id))
    device.ultimo_syslog = datetime.utcnow()
    return device


def fortigate_fields(message):
    fields = {}
    for match in re.finditer(r'\b([a-zA-Z_][\w.-]*)=(?:"((?:\\.|[^"\\])*)"|([^\s]+))', message or ""):
        fields[match[1]] = re.sub(r'\\(["\\])', r'\1', match[2]) if match[2] is not None else match[3]
    return fields


def sync_device_name(db, message):
    fields = fortigate_fields(message)
    serial, name = fields.get("devid"), fields.get("devname")
    if not serial or not name:
        return None
    identity = db.get(DeviceIdentity, serial)
    device = db.get(Device, identity.device_id) if identity else None
    if identity and device is None:
        # El equipo fue borrado del inventario: no reutilizar su identidad.
        return None
    if device is None:
        # Primera asociacion: buscar nombres historicos del MISMO serial.
        names = {name}
        previous = db.query(SyslogEvent).filter(SyslogEvent.mensaje.contains(serial)).all()
        for event in previous:
            old = fortigate_fields(event.mensaje)
            if old.get("devid") == serial:
                names.add(event.hostname)
                if old.get("devname"):
                    names.add(old["devname"])
        candidates = db.query(Device).filter(Device.nombre.in_(names), Device.marca == "Fortinet").all()
        candidates = [candidate for candidate in candidates
                      if db.query(DeviceIdentity).filter(DeviceIdentity.device_id == candidate.id).first() is None]
        if len(candidates) != 1:
            return None  # No asociar por una suposicion ni crear duplicados.
        device = candidates[0]
        db.add(DeviceIdentity(serial=serial, device_id=device.id))
    if device.nombre != name:
        device.nombre = name
    return device


def sync_latest_device_names(db):
    seen = set()
    for event in db.query(SyslogEvent).order_by(SyslogEvent.id.desc()).yield_per(100):
        fields = fortigate_fields(event.mensaje)
        serial = fields.get("devid")
        if serial and fields.get("devname") and serial not in seen:
            seen.add(serial)
            sync_device_name(db, event.mensaje)
