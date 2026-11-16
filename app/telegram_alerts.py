"""Alertas nuevas de Syslog Center a Telegram. Configurar: --setup."""
import argparse
import getpass
import hashlib
import json
import logging
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from app.alert_rules import classify_event

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".telegram.json"
STATE = ROOT / ".telegram-state.json"
LOG = logging.getLogger("telegram_alerts")
LEVELS = {0: "Emergency", 1: "Alert", 2: "Critical", 3: "Error"}


class DeliveryError(Exception):
    def __init__(self, message, retry_after=15):
        super().__init__(message)
        self.retry_after = retry_after


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(4):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.15 * (attempt + 1))


def telegram_call(token, method, payload):
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
    except HTTPError as error:
        delay = 15
        try:
            delay = max(15, int(json.loads(error.read()).get("parameters", {}).get("retry_after", 15)))
        except (ValueError, TypeError):
            pass
        # No imprimir la excepcion: su URL contiene el token.
        raise DeliveryError(f"Telegram respondio HTTP {error.code}. Revisa el token, el chat y los permisos.", delay) from None
    except (URLError, OSError, ValueError):
        raise DeliveryError("No se pudo conectar con Telegram. Comprueba Internet.") from None
    if not result.get("ok"):
        raise DeliveryError("Telegram no acepto la solicitud. Revisa la configuracion.")
    return result.get("result")


def setup():
    print("Abre tu bot en Telegram, pulsa Iniciar y enviale un mensaje como /start.")
    token = getpass.getpass("Token de BotFather (oculto): ").strip()
    if not token:
        raise ValueError("El token no puede estar vacio")
    telegram_call(token, "getMe", {})
    updates = telegram_call(token, "getUpdates", {"timeout": 0, "limit": 100})
    chats = {}
    for update in updates:
        message = update.get("message") or update.get("channel_post") or update.get("my_chat_member") or {}
        chat = message.get("chat", {})
        if "id" in chat:
            chats[str(chat["id"])] = chat
    if not chats:
        raise ValueError("No hay chats disponibles. Envia /start al bot y ejecuta --setup otra vez.")
    options = list(chats.items())
    for number, (chat_id, chat) in enumerate(options, 1):
        name = chat.get("title") or chat.get("first_name") or chat.get("username") or "Chat"
        print(f"{number}. {name} ({chat.get('type', 'chat')}) - {chat_id}")
    index = int(input("Numero del chat que recibira las alertas: ")) - 1
    if not 0 <= index < len(options):
        raise ValueError("Seleccion de chat no valida")
    # Excluir secretos del repositorio antes de escribir el archivo.
    ignore = ROOT / ".gitignore"
    content = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    entries = [".telegram.json", ".telegram.json.tmp", ".telegram-state.json", ".telegram-state.json.tmp"]
    missing = [entry for entry in entries if entry not in content.splitlines()]
    if missing:
        with ignore.open("a", encoding="utf-8") as stream:
            stream.write("\n" + "\n".join(missing) + "\n")
    save_json(CONFIG, {"token": token, "chat_id": options[index][0],
                       "api_url": "http://127.0.0.1:8000/syslog", "cooldown_seconds": 300})
    print("Configuracion guardada localmente. No se envio ningun mensaje.")
    print("Inicia con: python -m app.telegram_alerts")


def fields(message):
    return {m[1]: re.sub(r'\\(["\\])', r'\1', m[2]) if m[2] is not None else m[3]
            for m in re.finditer(r'\b([a-zA-Z_][\w.-]*)=(?:"((?:\\.|[^"\\])*)"|([^\s]+))', message or "")}


def critical(event, config=None):
    severity = classify_event(event)["severity"]
    overrides = (config or {}).get("host_max_severity", {})
    maximum = overrides.get(event.get("hostname"), 2)
    return isinstance(severity, int) and not isinstance(severity, bool) and 0 <= severity <= maximum


def describe(event):
    classification = classify_event(event)
    if classification["mensaje_noc"]:
        return classification["mensaje_noc"]
    values = fields(event.get("mensaje", ""))
    text = values.get("msg") or values.get("logdesc") or event.get("mensaje", "Sin descripcion")
    if values.get("checkname"):
        text += " · Comprobacion: " + values["checkname"]
    return text


def event_key(event):
    values = fields(event.get("mensaje", ""))
    identity = [values.get("devid") or event.get("hostname"), event.get("severity"),
                values.get("logid"), values.get("checkname"), values.get("user"),
                values.get("srcip"), values.get("dstip"), describe(event)]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()


def format_alert(event):
    classification = classify_event(event)
    rule = (f"\nRegla NOC: {classification['regla_noc']} · Severidad original: {classification['severity_original']}"
            if classification["regla_noc"] else "")
    return (f"🔴 ALERTA NOC — {LEVELS.get(classification['severity'], 'Critical')}\n"
            f"Equipo: {str(event.get('hostname', '?'))[:150]}\n"
            f"Evento: {describe(event)[:700]}\n"
            f"Recepcion (UTC): {event.get('fecha', '?')}\n"
            f"ID: {event['id']}{rule}")


def process_events(events, state, config, send, persist, now):
    cooldown = int(config.get("cooldown_seconds", 300))
    state["sent"] = {key: timestamp for key, timestamp in state.get("sent", {}).items()
                     if now - timestamp < cooldown}
    for event in sorted(events, key=lambda item: item["id"]):
        if event["id"] <= state["last_id"]:
            continue
        if critical(event, config):
            key = event_key(event)
            if key not in state["sent"]:
                send(format_alert(event))
                state["sent"][key] = now
                LOG.info("Alerta enviada: evento %s", event["id"])
                state["last_id"] = event["id"]
                persist(state)
        state["last_id"] = event["id"]
    # Una escritura para el lote rutinario, no una por cada evento.
    persist(state)


def run():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    LOG.info("Notificador activo: severidad general 0 a 2; repetidas silenciadas 5 minutos")
    for hostname, maximum in config.get("host_max_severity", {}).items():
        LOG.info("Filtro especifico: %s, severidad 0 a %s", hostname, maximum)
    while True:
        delay = 5
        stage = "consultar la API local"
        try:
            with urlopen(config["api_url"], timeout=10) as response:
                events = json.load(response)
            if state is None:
                state = {"last_id": max((event["id"] for event in events), default=0), "sent": {}}
                stage = "guardar el estado local"
                save_json(STATE, state)
                LOG.info("Punto inicial guardado. Solo se notificaran eventos nuevos.")
            else:
                stage = "procesar eventos o guardar el estado local"
                process_events(events, state, config,
                    lambda text: telegram_call(config["token"], "sendMessage", {
                        "chat_id": config["chat_id"], "text": text}),
                    lambda value: save_json(STATE, value), time.time())
        except DeliveryError as error:
            LOG.warning("%s Se reintentara.", error)
            delay = error.retry_after
        except (URLError, OSError, ValueError, KeyError, TypeError) as error:
            # No registrar URLs ni contenido de configuracion: contienen secretos.
            code = getattr(error, "winerror", None) or getattr(error, "errno", None) or getattr(error, "code", None)
            reason = getattr(error, "reason", None)
            detail = type(reason).__name__ if reason is not None else type(error).__name__
            LOG.warning("Fallo al %s: %s (codigo=%s). Se reintentara.", stage, detail, code)
            delay = 15
        time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        setup() if args.setup else run()
    except KeyboardInterrupt:
        print("\nNotificador detenido")
    except FileNotFoundError:
        parser.exit(1, "Primero ejecuta: python -m app.telegram_alerts --setup\n")
    except (DeliveryError, ValueError, OSError):
        parser.exit(1, "No se pudo completar la configuracion. Comprueba el token, /start al bot, la seleccion del chat y la conexion; no compartas el token.\n")


if __name__ == "__main__":
    main()
