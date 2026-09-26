# SUPERAGENTE GLSYSTEMS — Plantilla de superagente para negocios

Superagente de Telegram que administra un negocio: reservas, pedidos,
cobros, preguntas frecuentes e informe diario al dueño.
100% gratuito: corre en GitHub Actions, sin tarjeta, sin suscripción.

Modelo GLSystems: 10 consultas gratuitas por cliente al mes; después se
cobra por resultados, nunca suscripción.

## DESPLIEGUE EN 2 PASOS

1. Crea un bot con @BotFather en Telegram y copia su token.
2. En este repo: Settings → Secrets and variables → Actions → New
   repository secret → nombre `TELEGRAM_TOKEN`, valor = el token.

Listo. El workflow corre cada 5 minutos y atiende solo.

## ONBOARDING POR ENTREVISTA

En el primer mensaje, el superagente NO pregunta «qué deseas»: ENTREVISTA
al dueño (nombre del negocio, horario, servicios, precios) y se
auto-configura. Todo queda en `perfil_negocio.json`.

## COMANDOS DEL DUEÑO

`/informe` — resumen del día (reservas, pedidos, consultas)
`/perfil` — ver el perfil configurado del negocio

## ARCHIVOS

- `cerebro.py` — núcleo: intenciones, memoria, entrevista, límite 10
  consultas gratis/mes por cliente (registro en `consultas.json`)
- `agente_telegram.py` — consumidor de mensajes (una pasada, para cron)
- `perfil_negocio.json` — configuración del negocio (se llena solo)
- `.github/workflows/superagente.yml` — latido cada 5 minutos, gratis

## REGLA DE MARCA

Este superagente es cortesía de GLSystems. No se cobra tarjeta ni
suscripción: se cobra por resultados, cuando el negocio gana.
