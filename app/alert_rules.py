"""Reglas NOC compartidas por dashboard y Telegram; no alteran el log original."""
import re


def classify_event(event):
    raw = event.get("mensaje", "") or ""
    fields = {}
    for match in re.finditer(r'\b([a-zA-Z_][\w.-]*)=(?:"((?:\\.|[^"\\])*)"|([^\s]+))', raw):
        fields[match[1]] = re.sub(r'\\(["\\])', r'\1', match[2]) if match[2] is not None else match[3]
    original = event.get("severity")
    result = {"severity": original, "severity_original": original,
              "regla_noc": None, "mensaje_noc": None}
    if "MIKROTIK" in str(event.get("hostname", "")).upper():
        # RouterOS envia reinicios y cambios de interfaces como info (nivel 6).
        header = re.match(r'^<\d+>[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\S+\s+(.*)', raw)
        body = header[1] if header else raw
        down = re.search(r'\b([\w.-]+)\s+link\s+down\b', body, re.I)
        admin_down = re.search(r'\(/interface(?:\s+ethernet)?\s+set\s+([\w.-]+)\s+[^)]*\bdisabled=yes\b', body, re.I)
        admin_disable = re.search(r'\(/interface(?:\s+ethernet)?\s+disable\s+([\w.-]+)\s*\)', body, re.I)
        if re.search(r'\brouter (?:was )?rebooted\b', body, re.I):
            result.update(regla_noc="mikrotik_reboot", mensaje_noc="Reinicio del equipo MikroTik registrado")
        elif down:
            result.update(regla_noc="mikrotik_interface_down", mensaje_noc=f"Interfaz {down[1]} caida (DOWN)")
        elif admin_down or admin_disable:
            match = admin_down or admin_disable
            result.update(regla_noc="mikrotik_interface_admin_down",
                          mensaje_noc=f"Interfaz {match[1]} deshabilitada administrativamente")
        if result["regla_noc"]:
            result["severity"] = min(original, 2) if isinstance(original, int) else 2
        return result
    if not (fields.get("devid", "").startswith("FG") and fields.get("type") == "event"):
        return result
    description = fields.get("logdesc", "").lower()
    interface = fields.get("intf") or fields.get("interface") or fields.get("cfgobj") or "sin identificar"
    if fields.get("status", "").upper() == "DOWN" and (
            fields.get("action") == "interface-stat-change" or description == "interface status changed"):
        result.update(regla_noc="fortigate_interface_down", mensaje_noc=f"Interfaz {interface} caida (DOWN)")
    elif fields.get("cfgpath") == "system.interface" and re.search(
            r"\bstatus\[up\s*->\s*down\]", fields.get("cfgattr", ""), re.I):
        result.update(regla_noc="fortigate_interface_admin_down",
                      mensaje_noc=f"Interfaz {interface} deshabilitada administrativamente" +
                      (f" · Usuario: {fields['user']}" if fields.get("user") else ""))
    if result["regla_noc"]:
        result["severity"] = min(original, 2) if isinstance(original, int) else 2
    return result
