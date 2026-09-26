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


## Canal Matrix cifrado (sin Meta) — `agente_matrix.py`

Interacción bot-usuario con cifrado EXTREMO A EXTREMO real (protocolo
Matrix, estándar abierto y auditado). La conversación no pasa por
plataformas de Meta ni por servidores que puedan leerla.

### Por qué Matrix y no otras
- Telegram: chats de bots SIN cifrado extremo a extremo (quedan en los
  servidores de Telegram). Solo los chats secretos son E2E y los bots no
  pueden usarlos.
- Signal: mejor cifrado del mercado, pero SIN API de bots y exige demonio
  24/7 con número real: inviable gratis con GitHub Actions.
- Matrix con la app Element: E2EE real, API de bots oficial gratuita,
  app del cliente gratis sin número de teléfono ni tarjeta, y
  descentralizado (podemos montar servidor propio después sin cambiar
  nada para el cliente).

### Puesta en marcha (10 min, 100% gratis, sin tarjeta)
1. Crear la cuenta del superagente en matrix.org (o el homeserver que
   se elija) desde element.io: gratis, no pide tarjeta.
2. Agregar secretos al repo: MATRIX_HOMESERVER, MATRIX_USUARIO,
   MATRIX_PASSWORD, MATRIX_FRASE (frase del almacén criptográfico).
3. El dueño instala Element (iOS/Android/Web), crea una sala con
   «activar cifrado» (por defecto en salas nuevas) e invita al usuario
   del bot.
4. El dueño escribe /start en la sala: arranca la entrevista de
   configuración del negocio (mismo flujo que Telegram).
5. Cada cliente que el dueño invite a la sala queda atendido con el
   límite de 10 consultas gratis/mes; el resto, plan por resultados.

### Arquitectura de una pasada (regla de un solo consumidor)
GitHub Actions corre `agente_matrix.py` cada 5 minutos: sincroniza con
el token guardado en memoria.json (equivalente al offset de Telegram),
responde y desconecta. La sesión (access_token + device_id) y las
claves criptográficas (matrix_cripto.db) se persisten en el repo, así
el bot es SIEMPRE el mismo dispositivo E2E entre corridas.
