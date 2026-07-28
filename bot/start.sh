#!/bin/bash
# Avvia il bot Discord in background
python3 bot/bot.py &

# Avvia il server Node.js in primo piano (gestisce l'health check del deployment)
node --enable-source-maps artifacts/api-server/dist/index.mjs
