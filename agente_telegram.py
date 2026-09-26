#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SUPERAGENTE GLSYSTEMS — Consumidor Telegram de una pasada.
Diseñado para GitHub Actions cada 5 minutos: SIN daemon, SIN doble
consumidor (regla de un solo consumidor). 100% gratuito."""
import json, os, sys, urllib.request, urllib.parse, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cerebro

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"
BASE = os.path.dirname(os.path.abspath(__file__))
F_REG = os.path.join(BASE, "registros.json")

def tg(metodo, **datos):
    datos.setdefault("parse_mode", "Markdown")
    data = json.dumps(datos).encode()
    req = urllib.request.Request(f"{API}/{metodo}", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return json.load(r)
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode()[:200]
        if datos.get("parse_mode") == "Markdown":
            datos.pop("parse_mode", None)
            req = urllib.request.Request(f"{API}/{metodo}",
                data=json.dumps(datos).encode(),
                headers={"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=30))
        print(f"tg {metodo} error: {cuerpo}")
        return None

def main():
    h = cerebro.cargar_historial()
    perfil = cerebro.cargar_perfil()
    try:
        registros = json.load(open(F_REG, encoding="utf-8"))
    except Exception:
        registros = {}

    r = tg("getUpdates", offset=h["offset"], timeout=0)
    actualizaciones = (r or {}).get("result", [])
    for upd in actualizaciones:
        h["offset"] = upd["update_id"] + 1
        msg = upd.get("message") or upd.get("edited_message")
        if not msg or not msg.get("text"):
            continue
        chat_id = msg["chat"]["id"]
        texto = msg["text"].strip()
        estado = h["clientes"].setdefault(str(chat_id), {"mes": cerebro.mes_actual(), "n": 0, "dueño": False})
        estado.setdefault("entrevista", None)

        if texto.startswith("/start"):
            if not perfil.get("completo"):
                estado["entrevista"] = 0
                cerebro.registrar_dueno(chat_id, h)
                tg("sendMessage", chat_id=chat_id, text=(
                    "¡Hola! Soy tu *superagente GLSystems*. 👋\n\n"
                    "Antes de atender clientes necesito conocerte: te haré "
                    "5 preguntas rápidas y con eso quedo configurado para "
                    "tu negocio. Empecemos."))
                tg("sendMessage", chat_id=chat_id, text=cerebro.PASOS[0][1])
                continue
        if texto == "/informe":
            if cerebro.es_dueno(chat_id, h):
                tg("sendMessage", chat_id=chat_id, text=cerebro.informe_diario(perfil, registros))
            else:
                tg("sendMessage", chat_id=chat_id, text="Ese informe es solo para el dueño. ¿Te ayudo con algo del negocio?")
            continue
        if texto == "/perfil":
            tg("sendMessage", chat_id=chat_id, text="```\n" + json.dumps(perfil, ensure_ascii=False, indent=1) + "\n```")
            continue

        permitida, restantes, es_dueno = cerebro.consultar_cuota(chat_id, h)
        if not permitida and not es_dueno:
            tg("sendMessage", chat_id=chat_id, text=(
                "Ya usaste tus *10 consultas gratis* de este mes. 🌟\n"
                "El plan GLSystems sigue activo para el negocio; para "
                "seguir consultando como cliente, escríbele al dueño y "
                "te activa el plan por resultados."))
            continue

        respuesta = cerebro.responder(texto, perfil, estado, registros)
        if not es_dueno and isinstance(restantes, int) and restantes <= 3 and not perfil.get("completo") is False:
            respuesta += f"\n\n_(Consultas gratis restantes este mes: {restantes})_"
        tg("sendMessage", chat_id=chat_id, text=respuesta)

    json.dump(registros, open(F_REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    cerebro.guardar_historial(h)

if __name__ == "__main__":
    if not TOKEN:
        print("Falta TELEGRAM_TOKEN"); sys.exit(0)
    main()
