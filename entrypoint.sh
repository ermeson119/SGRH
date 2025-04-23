#!/bin/bash

# Espera até que o Redis esteja disponível
echo "Aguardando o Redis..."
while ! redis-cli -h redis -p 6379 ping > /dev/null 2>&1; do
    echo "Redis não está disponível - aguardando 1 segundo..."
    sleep 1
done
echo "Redis está disponível!"

# Inicia o Flask
exec flask run