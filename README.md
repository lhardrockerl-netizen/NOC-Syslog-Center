# NOC Syslog Center

Aplicación académica para centralizar registros syslog de equipos de red, visualizar eventos importantes y enviar alertas a Telegram.

Desarrollada con Python, FastAPI, SQLite y HTML/CSS/JavaScript. Probada con FortiGate y MikroTik CHR en un laboratorio GNS3.

## Funcionalidades

- Recepción de syslog por UDP.
- Almacenamiento de eventos en SQLite.
- Inventario de equipos.
- Clasificación por severidad.
- Mensajes resumidos y consulta del registro original.
- Vista de eventos importantes y opción «Ver todos».
- Filtros desde las tarjetas del dashboard.
- Actualización automática cada cinco segundos.
- Actualización del hostname de FortiGate mediante su identificador de dispositivo.
- Gestión de incidentes.
- Generador de configuración syslog para Cisco, Fortinet y Huawei.
- Notificaciones a Telegram con control de alertas repetidas.

El generador de configuración no implica que todos los fabricantes hayan sido probados. La integración actual se verificó con FortiGate y MikroTik.

## Tecnologías

- Python
- FastAPI y Uvicorn
- SQLAlchemy
- SQLite
- HTML, CSS y JavaScript
- Telegram Bot API
- GNS3 y VMware para el laboratorio

## Instalación

Desde la carpeta del proyecto:


python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install fastapi uvicorn sqlalchemy


## Ejecución

Se requieren tres terminales, con el entorno virtual activo.

### 1. API


python -m uvicorn app.main:app --reload


Documentación interactiva:

http://127.0.0.1:8000/docs

### 2. Receptor syslog


python -m app.syslog_receiver --port 514 --allow-source 192.168.125.200 --allow-source 192.168.125.201 --allow-source 127.0.0.1


Las direcciones permitidas deben coincidir con las IP de los equipos del laboratorio.

### 3. Telegram

Primera configuración:


python -m app.telegram_alerts --setup


El asistente solicita el token del bot y permite seleccionar el chat de destino. Antes de configurarlo, enviar `/start` al bot desde Telegram.

Iniciar el notificador:


python -m app.telegram_alerts


Finalmente, abrir `frontend/index.html` en el navegador.

## Laboratorio utilizado

| Servidor Windows / VMnet1 | 192.168.125.1 |
| FortiGate | 192.168.125.200 |
| MikroTik CHR | 192.168.125.201 |

Los equipos se conectan mediante un switch Ethernet de GNS3 al Cloud asociado con la interfaz Host-only de la GNS3 VM.

El servidor Windows debe permitir tráfico entrante UDP 514 desde las IP autorizadas.

## Configuración de FortiGate


config log syslogd setting
    set status enable
    set server "192.168.125.1"
    set mode udp
    set port 514
    set source-ip "192.168.125.200"
end

config log syslogd filter
    set severity information
end


## Configuración de MikroTik

Ejemplo para una versión de RouterOS que admite `remote-log-format=syslog`:


/system identity set name=RTR-MIKROTIK-BOG

/system logging action add name=noc-syslog target=remote remote=192.168.125.1 remote-port=514 src-address=192.168.125.201 remote-log-format=syslog syslog-facility=local0 syslog-severity=auto

/system logging add topics=warning action=noc-syslog
/system logging add topics=error action=noc-syslog
/system logging add topics=critical action=noc-syslog
/system logging add topics=system,info action=noc-syslog
/system logging add topics=interface,info action=noc-syslog
```

Crear las reglas una sola vez para evitar envíos duplicados.

## Severidad y reglas de alertamiento

| Nivel syslog | Nombre |
|---|---|
| 0 | Emergency |
| 1 | Alert |
| 2 | Critical |
| 3 | Error |
| 4 | Warning |
| 5 | Notice |
| 6 | Informational |
| 7 | Debug |

Por defecto, Telegram notifica eventos nuevos de niveles 0 a 2.

En el laboratorio también se configuró una excepción para incluir los errores de `RTR-MIKROTIK-BOG`, nivel 3, mediante `host_max_severity` en la configuración local.

Las reglas NOC elevan a Critical determinados eventos operativos:

- FortiGate: interfaz DOWN o deshabilitada administrativamente.
- MikroTik: interfaz DOWN, deshabilitación administrativa y reinicio registrado.

La severidad original y el mensaje completo permanecen almacenados. La prioridad NOC es una clasificación adicional de la aplicación.

Los eventos de recuperación UP no se elevan automáticamente a Critical.

## Notificaciones a Telegram

Cada alerta incluye el equipo, la severidad, una descripción y la fecha de recepción en UTC.

- En el primer inicio no se notifican eventos históricos.
- El estado local permite continuar desde el último evento procesado.
- La misma alerta se silencia durante cinco minutos.
- El archivo de configuración y el estado se excluyen mediante `.gitignore`.

No publicar el token del bot ni los archivos `.telegram.json` y `.telegram-state.json`.

## Verificación

Se realizaron pruebas de:

- Recepción UDP y almacenamiento mediante la API.
- Interpretación de hostname, facility y severidad.
- Filtros del dashboard.
- Actualización del inventario de FortiGate.
- Reglas para caídas de interfaces y reinicios.
- Envío de notificaciones a Telegram.
- Control de alertas repetidas.

## Limitaciones

- UDP no garantiza la entrega.
- El receptor actual no tiene una cola persistente: si la API no está disponible, el evento recibido puede perderse.
- Una caída del enlace usado para syslog puede impedir que llegue la alerta.
- El estado «Activo» del inventario no equivale a una comprobación continua de disponibilidad.
- La consola del dashboard es simulada y de solo lectura.
- La aplicación está orientada a un laboratorio local; requiere autenticación y otras mejoras antes de exponerse a Internet.
- Las reglas de MikroTik actuales identifican al equipo por su hostname, que debe mantenerse coherente con la configuración.

## Autor

Jhon Helber Chico

Proyecto académico para la asignatura Administración y Gestión de Redes.