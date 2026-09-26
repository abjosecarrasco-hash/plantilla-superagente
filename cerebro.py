#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CEREBRO DEL SUPERAGENTE GLSYSTEMS (plantilla Línea F, 26-sep-2026)
Núcleo mínimo y robusto: intenciones, memoria, entrevista de onboarding,
límite de 10 consultas gratis/mes por cliente, informe diario al dueño.
Sin dependencias externas: solo stdlib. 100% gratuito."""
import json, os, re, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
F_PERFIL = os.path.join(BASE, "perfil_negocio.json")
F_HIST = os.path.join(BASE, "memoria.json")
F_CONS = os.path.join(BASE, "consultas.json")

CONSULTAS_GRATIS = 10

def _cargar(ruta, defecto):
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except Exception:
        return defecto

def _guardar(ruta, dato):
    json.dump(dato, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def cargar_perfil():
    return _cargar(F_PERFIL, {"nombre": "", "horario": "", "servicios": [], "precios": {}, "dueño": "", "completo": False})

def guardar_perfil(p):
    _guardar(F_PERFIL, p)

def cargar_historial():
    return _cargar(F_HIST, {"offset": 0, "clientes": {}})

def guardar_historial(h):
    _guardar(F_HIST, h)

def mes_actual():
    return datetime.date.today().strftime("%Y-%m")

def consultar_cuota(cliente_id, h):
    """Cuenta una consulta del mes. Devuelve (permitida, restantes, es_dueno)."""
    c = h["clientes"].setdefault(str(cliente_id), {"mes": mes_actual(), "n": 0, "dueño": False})
    if c["mes"] != mes_actual():
        c["mes"], c["n"] = mes_actual(), 0
    if c["dueño"]:
        return True, "∞", True
    if c["n"] >= CONSULTAS_GRATIS:
        return False, 0, False
    c["n"] += 1
    return True, CONSULTAS_GRATIS - c["n"], False

def es_dueno(cliente_id, h):
    c = h["clientes"].get(str(cliente_id))
    return bool(c and c.get("dueño"))

def registrar_dueno(cliente_id, h):
    h["clientes"].setdefault(str(cliente_id), {"mes": mes_actual(), "n": 0, "dueño": True})["dueño"] = True

# ---------- ENTREVISTA DE ONBOARDING (reverse prompting) ----------

PASOS = [
    ("nombre", "¿Cómo se llama tu negocio?"),
    ("dueño", "¿Tu nombre completo, para firmar los informes?"),
    ("horario", "¿Qué horario atiendes? (ej.: lun-sáb 9:00-21:00)"),
    ("servicios", "¿Qué vendes o ofreces? Separa cada cosa con comas."),
    ("precios", "Y para terminar: ¿qué precios o tarifas manejas? Puedes poner varios."),
]

def paso_entrevista(texto, perfil, i):
    """Guarda la respuesta y devuelve (mensaje, i+1 o None si terminó)."""
    clave = PASOS[i][0]
    if clave == "servicios":
        perfil["servicios"] = [s.strip() for s in texto.split(",") if s.strip()]
    elif clave == "precios":
        perfil["precios"] = {"principal": texto.strip()}
    else:
        perfil[clave] = texto.strip()
    i += 1
    if i >= len(PASOS):
        perfil["completo"] = True
        guardar_perfil(perfil)
        return (f"Listo. {perfil['nombre']} queda configurado.\n\n"
                "Ya puedes recibir clientes: dime «quiero reservar», «cuánto cuesta» "
                "o «quiero pedir» y yo atiendo. Escribe /informe cuando quieras el resumen del día."), None
    return PASOS[i][1], i

# ---------- INTENCIONES DE CLIENTE ----------

def responder(texto, perfil, estado, registros):
    """Responde un mensaje de cliente. `estado` lleva la entrevista."""
    t = texto.lower()
    if not perfil.get("completo"):
        if estado.get("entrevista") is None:
            estado["entrevista"] = 0
            return PASOS[0][1]
        msg, nuevo = paso_entrevista(texto, perfil, estado["entrevista"])
        estado["entrevista"] = nuevo
        return msg

    # 1. horario primero: "a qué hora atienden" NO es una reserva
    if "horario" in t or "atienden" in t or "abierto" in t or "abren" in t or "cierran" in t:
        return f"El horario de {perfil['nombre']} es {perfil.get('horario', 'por definir')}."

    # 2. precios
    if "cuánto" in t or "cuanto" in t or "precio" in t or "cuesta" in t or "tarifa" in t or "vale" in t:
        precios = perfil.get("precios", {})
        lista = precios.get("principal", "consultar en el negocio") if isinstance(precios, dict) else str(precios)
        return f"Nuestros precios: {lista}. ¿Te ayudo a reservar o pedir?"

    # 3. reservas (solo con palabras claras)
    if "reserv" in t or "mesa" in t or "cita" in t or "turno" in t:
        registros.setdefault("reservas", []).append(
            {"texto": texto, "fecha": datetime.datetime.now().isoformat(timespec="minutes")})
        return ("¡Reserva anotada! 📅 Te confirmo por aquí mismo con "
                f"{perfil['nombre']}. Si necesitas cambiarla, escríbeme.")

    # 4. pedidos
    if "pedir" in t or "pedido" in t or "orden" in t or "comprar" in t or "quiero" in t:
        registros.setdefault("pedidos", []).append(
            {"texto": texto, "fecha": datetime.datetime.now().isoformat(timespec="minutes")})
        return "¡Pedido registrado! 🧾 Te confirmo enseguida. ¿Algo más?"

    return (f"Soy el asistente de {perfil['nombre']}. Puedo ayudarte con reservas, "
            "pedidos, precios y horarios. ¿Qué necesitas?")

def informe_diario(perfil, registros):
    hoy = datetime.date.today().isoformat()
    lin = [f"INFORME DE {perfil['nombre']} — {hoy}", ""]
    for k, titulo in (("reservas", "Reservas"), ("pedidos", "Pedidos")):
        items = [r for r in registros.get(k, []) if r["fecha"].startswith(hoy)]
        lin.append(f"{titulo}: {len(items)}")
        for r in items:
            lin.append(f"  • {r['texto'][:80]} ({r['fecha'][11:16]})")
    if not any(l.startswith(("Reservas", "Pedidos")) for l in lin):
        lin.append("Hoy aún no hay movimiento registrado.")
    return "\n".join(lin)
