#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUPERAGENTE GLSYSTEMS — Canal MATRIX cifrado (E2EE), consumidor de una pasada.
Diseñado para GitHub Actions cada 5 minutos: SIN daemon, SIN doble
consumidor (regla de un solo consumidor). 100% gratuito, sin Meta.
Cifrado extremo a extremo: la conversación no pasa por servidores que
puedan leerla (protocolo Matrix, estándar abierto y auditado).

Requisitos: pip install "matrix-nio[e2e]" (v0.26+)
Secretos (GitHub): MATRIX_HOMESERVER, MATRIX_USUARIO, MATRIX_PASSWORD,
MATRIX_FRASE (passphrase que cifra el almacén Olm local).

Persistencia PRIVADA entre corridas (repo público: NADA de tokens en git):
  - artefacto "estado-matrix": matrix_sesion.json (access_token + device_id)
    y matrix_cripto.db (claves E2E cifradas con MATRIX_FRASE)
  - memoria.json / registros.json / perfil_negocio.json: en git (sin secretos)
"""
import asyncio, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cerebro

from nio import (AsyncClient, AsyncClientConfig, LoginResponse,
                  RoomMessageText, SyncResponse)

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

    # --- sesión persistente: leer ANTES de construir el cliente ---
    sesion = {}
    if os.path.exists(F_SESION):
        try:
            sesion = json.load(open(F_SESION, encoding="utf-8"))
        except Exception:
            sesion = {}
    config = AsyncClientConfig(encryption_enabled=True,
                               store_sync_tokens=True,
                               pickle_key=FRASE,
                               store_name="matrix_cripto.db")
    # device_id conocido => nio crea el almacén E2E desde el constructor
    cliente = AsyncClient(HOMESERVER, USUARIO,
                          device_id=sesion.get("device_id", ""),
                          store_path=BASE, config=config)
    if sesion.get("access_token") and sesion.get("device_id"):
        cliente.restore_login(user_id=USUARIO,
                              device_id=sesion["device_id"],
                              access_token=sesion["access_token"])
        print("sesión restaurada, device:", sesion["device_id"])
    else:
        resp = await cliente.login(PASSWORD, device_name="Superagente GLSystems")
        if not isinstance(resp, LoginResponse):
            print("login falló:", resp); await cliente.close(); return
        json.dump({"access_token": resp.access_token, "device_id": resp.device_id},
                  open(F_SESION, "w", encoding="utf-8"))
        print("login nuevo, device:", resp.device_id)

    # --- claves E2E: load_store CREA el almacén si no existe, o lo carga ---
    try:
        res = cliente.load_store()          # síncrono en nio 0.26
        if hasattr(res, "__await__"):
            await res
        print("store cripto activo (olm listo)")
    except Exception as e:
        print("store cripto falló:", e)

    h = cerebro.cargar_historial()
    perfil = cerebro.cargar_perfil()
    try:
        registros = json.load(open(F_REG, encoding="utf-8"))
    except Exception:
        registros = {}

    desde = h.get("matrix_since")
    sync = await cliente.sync(timeout=0, since=desde, full_state=False)
    if not isinstance(sync, SyncResponse):
        print("sync falló:", sync); await cliente.close(); return
    h["matrix_since"] = sync.next_batch
    print("sync ok, salas:", len(sync.rooms.join or {}))

    async def enviar(room_id, texto):
        await cliente.room_send(room_id, "m.room.message",
                                {"msgtype": "m.text", "body": texto})

    # REGLA ANTI-SPAM: solo salas con invitación explícita (DMs/invites
    # reales). Las salas automáticas (bienvenida de matrix.org, salas
    # públicas) se ignoran: el bot jamás responde donde no lo invitaron.
    activas = h.setdefault("salas_activas", {})
    for room_id in list((sync.rooms.invite or {}).keys()):
        try:
            await cliente.join(room_id)
            activas[room_id] = True
            print("invitación aceptada, sala activa:", room_id)
        except Exception as e:
            print("no pude unirme a", room_id, e)

    for room_id, sala in (sync.rooms.join or {}).items():
        if room_id not in activas:
            continue
        for evento in getattr(getattr(sala, "timeline", None), "events", []) or []:
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
