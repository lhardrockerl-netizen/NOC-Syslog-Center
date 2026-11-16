"""Actualiza nombres de inventario por el devid estable de FortiGate."""
import re

from app.models import Device, DeviceIdentity, SyslogEvent


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
