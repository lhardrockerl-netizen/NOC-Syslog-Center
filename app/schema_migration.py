"""Migracion aditiva para conservar bases SQLite existentes."""
from sqlalchemy import inspect, text


def ensure_inventory_columns(engine):
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "ultimo_syslog" not in {col["name"] for col in inspector.get_columns("devices")}:
            connection.execute(text("ALTER TABLE devices ADD COLUMN ultimo_syslog DATETIME"))
        if "source_ip" not in {col["name"] for col in inspector.get_columns("syslog_events")}:
            connection.execute(text("ALTER TABLE syslog_events ADD COLUMN source_ip VARCHAR"))
