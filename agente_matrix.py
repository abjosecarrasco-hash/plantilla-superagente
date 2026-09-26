#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUPERAGENTE GLSYSTEMS — Canal MATRIX cifrado (E2EE), consumidor de una pasada.
Diseñado para GitHub Actions cada 5 minutos: SIN daemon, SIN doble
consumidor (regla de un solo consumidor). 100% gratuito, sin Meta.
Cifrado extremo a extremo: la conversación no pasa por servidores que
puedan leerla (protocolo Matrix, estándar abierto y auditado).

Requisitos: pip install "matrix-nio[e2e]"
Secretos (GitHub): MATRIX_HOMESERVER, MATRIX_USUARIO, MATRIX_PASSWORD,
MATRIX_FRASE (passphrase del almacén criptográfico local).

Persistencia en el repo (sobrevive entre corridas):
  - matrix_sesion.json : access_token + device_id (dispositivo estable)
  - matrix_cripto.db   : claves Olm/Megolm (cifrado E2E)
  - memoria.json       : token de sincronización + estado de clientes
"""
import asyncio, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cerebro

from nio import AsyncClient, LoginResponse, RoomMessageText, SyncResponse

BASE = os.path.dirname(os.path.abspath(__file__))
F_SESION = os.path.join(BASE, "matrix_sesion.json")
F_CRIPTO = os.path.join(BASE, "matrix_cripto.db")
F_REG = os.path.join(BASE, "registros.json")

HOMESERVER = os.environ.get("MATRIX_HOMESERVER", "https://matrix.org")
USUARIO = os.environ.get("MATRIX_USUARIO", "")
PASSWORD = os.environ.get("MATRIX_PASSWORD", "")
FRASE = os.environ.get("MATRIX_FRASE", "glsystems")

async def main():
    if not USUARIO or not PASSWORD:
        print("Faltan MATRIX_USUARIO o MATRIX_PASSWORD"); return

    cliente = AsyncClient(HOMESERVER, USUARIO)
    cliente.user_id = USUARIO

    # --- sesión persistente: un MISMO dispositivo en cada corrida ---
    sesion = {}
    if os.path.exists(F_SESION):
        try:
            sesion = json.load(open(F_SESION, encoding="utf-8"))
        except Exception:
            sesion = {}
    if sesion.get("access_token") and sesion.get("device_id"):
        cliente.restore_login(user_id=USUARIO,
                              device_id=sesion["device_id"],
                              access_token=sesion["access_token"])
    else:
        resp = await cliente.login(PASSWORD, device_name="Superagente GLSystems")
        if not isinstance(resp, LoginResponse):
            print("login falló:", resp); return
        json.dump({"access_token": resp.access_token, "device_id": resp.device_id},
                  open(F_SESION, "w", encoding="utf-8"))
        cliente.device_id = resp.device_id

    # --- almacén criptográfico persistente (E2EE) ---
    try:
        cliente.load_store(F_CRIPTO, FRASE)
        print("store cripto cargado")
    except Exception as e:
        print("store cripto nuevo:", e)

    h = cerebro.cargar_historial()
    perfil = cerebro.cargar_perfil()
    try:
        registros = json.load(open(F_REG, encoding="utf-8"))
    except Exception:
        registros = {}

    # --- sincronización de una pasada con token guardado ---
    desde = h.get("matrix_since")
    sync = await cliente.sync(timeout=0, since=desde, full_state=False)
    if not isinstance(sync, SyncResponse):
        print("sync falló:", sync); await cliente.close(); return
    h["matrix_since"] = sync.next_batch

    async def enviar(room_id, texto):
        contenido = {"msgtype": "m.text", "body": texto}
        await cliente.room_send(room_id, "m.room.message", contenido)

    for room_id in (sync.rooms.join or {}):
        try:
            await cliente.join(room_id)
        except Exception:
            pass
        sala = sync.rooms.join[room_id]
        for evento in getattr(sala.timeline, "events", []) or []:
            if not isinstance(evento, RoomMessageText):
                continue
            if evento.sender == USUARIO:
                continue
            texto = (getattr(evento, "body", "") or "").strip()
            if not texto:
                continue
            estado = h["clientes"].setdefault(room_id,
                {"mes": cerebro.mes_actual(), "n": 0, "dueño": False})
            estado.setdefault("entrevista", None)

            if texto.startswith("/start"):
                if not perfil.get("completo"):
                    estado["entrevista"] = 0
                    cerebro.registrar_dueno(room_id, h)
                    await enviar(room_id, "¡Hola! Soy tu superagente GLSystems. 👋\n\n"
                        "Antes de atender clientes necesito conocerte: te haré 5 "
                        "preguntas rápidas y con eso quedo configurado para tu "
                        "negocio. Empecemos.")
                    await enviar(room_id, cerebro.PASOS[0][1])
                continue
            if texto == "/informe":
                if cerebro.es_dueno(room_id, h):
                    await enviar(room_id, cerebro.informe_diario(perfil, registros))
                else:
                    await enviar(room_id, "Ese informe es solo para el dueño. "
                                  "¿Te ayudo con algo del negocio?")
                continue
            if texto == "/perfil":
                await enviar(room_id, json.dumps(perfil, ensure_ascii=False, indent=1))
                continue

            permitida, restantes, es_dueno = cerebro.consultar_cuota(room_id, h)
            if not permitida and not es_dueno:
                await enviar(room_id, "Ya usaste tus 10 consultas gratis de este "
                    "mes. 🌟 El plan GLSystems sigue activo para el negocio; para "
                    "seguir consultando como cliente, escríbele al dueño y te "
                    "activa el plan por resultados.")
                continue
            respuesta = cerebro.responder(texto, perfil, estado, registros)
            await enviar(room_id, respuesta)

    json.dump(registros, open(F_REG, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    cerebro.guardar_historial(h)
    await cliente.close()

if __name__ == "__main__":
    asyncio.run(main())
