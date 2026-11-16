"""Receptor UDP para el laboratorio; entrega eventos a la API existente."""

import argparse
import json
import logging
import re
import socket
import ipaddress
from urllib.error import URLError
from urllib.request import Request, urlopen

LOG = logging.getLogger("syslog_receiver")
FACILITIES = (
    "kern", "user", "mail", "daemon", "auth", "syslog", "lpr", "news",
    "uucp", "cron", "authpriv", "ftp", "ntp", "audit", "alert", "clock",
    "local0", "local1", "local2", "local3", "local4", "local5", "local6", "local7",
)
LEVELS = {
    "emergency": 0, "emerg": 0, "alert": 1, "critical": 2, "crit": 2,
    "error": 3, "err": 3, "warning": 4, "warn": 4, "notice": 5,
    "information": 6, "informational": 6, "info": 6, "debug": 7,
}


def parse_message(data, source_ip):
    """Conserva el texto y extrae PRI, devname y encabezados habituales."""
    raw = data.decode("utf-8", errors="replace").rstrip("\r\n\x00")
    body = raw
    facility, severity = "user", 6
    pri = re.match(r"^<(\d{1,3})>", raw)
    if pri and 0 <= int(pri[1]) <= 191:
        value = int(pri[1])
        facility, severity = FACILITIES[value // 8], value % 8
        body = raw[pri.end():]
    else:
        level = re.search(r'\blevel=(?:"([^"\r\n]*)"|(\S+))', body)
        if level:
            severity = LEVELS.get((level[1] or level[2]).lower(), 6)

    hostname = source_ip
    devname = re.search(r'\bdevname=(?:"([^"\r\n]*)"|(\S+))', body)
    if devname:
        hostname = devname[1] or devname[2] or source_ip
    else:
        # RFC 5424: VERSION TIMESTAMP HOSTNAME APP-NAME ...
        modern = re.match(r"^\d{1,3} \S+ (\S+) ", body)
        legacy = re.match(r"^[A-Z][a-z]{2}\s+\d{1,2} \d{2}:\d{2}:\d{2} (\S+) ", body)
        header = modern or legacy
        if header and header[1] != "-":
            hostname = header[1]
    return dict(hostname=hostname, facility=facility, severity=severity, mensaje=raw, source_ip=source_ip)


def forward_event(event, api_url):
    request = Request(
        api_url, data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=5) as response:
        if not 200 <= response.status < 300:
            raise OSError(f"HTTP {response.status}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=514)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/syslog")
    parser.add_argument("--allow-source", action="append", default=[],
                        help="IP permitida; repetir para varios dispositivos")
    parser.add_argument("--allow-network", action="append", default=[],
                        help="Subred autorizada, por ejemplo 192.168.125.0/24")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535")
    try:
        networks = [ipaddress.ip_network(value) for value in args.allow_network]
    except ValueError:
        parser.error("Subred no valida en --allow-network")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((args.host, args.port))
            LOG.info("Escuchando UDP %s:%s -> %s", args.host, args.port, args.api_url)
            while True:
                data, address = sock.recvfrom(65535)
                if (args.allow_source or networks) and address[0] not in args.allow_source and not any(
                        ipaddress.ip_address(address[0]) in network for network in networks):
                    continue
                if not data:
                    continue
                event = parse_message(data, address[0])
                try:
                    forward_event(event, args.api_url)
                except (URLError, OSError, TimeoutError):
                    LOG.exception("No se guardo el evento de %s; comprueba la API", address[0])
                else:
                    LOG.info("Guardado: origen=%s hostname=%s severity=%s",
                             address[0], event["hostname"], event["severity"])
    except KeyboardInterrupt:
        LOG.info("Receptor detenido")
    except OSError as exc:
        parser.exit(1, f"No se pudo abrir el receptor UDP: {exc}\n")


if __name__ == "__main__":
    main()
