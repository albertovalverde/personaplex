#!/bin/bash

# Archivo fuente (ruta relativa desde scripts/)
SRC_FILE="../assets/test/pepper.pt"

# Directorio destino
DEST_DIR="$HOME/.cache/huggingface/hub/models--nvidia--personaplex-7b-v1/snapshots/3343b641d663e4c851120b3575cbdfa4cc33e7fa/voices"

# Verificar que el archivo fuente exista
if [ ! -f "$SRC_FILE" ]; then
    echo "Error: el archivo fuente $SRC_FILE no existe."
    exit 1
fi

# Verificar que el directorio destino exista
if [ ! -d "$DEST_DIR" ]; then
    echo "Error: el directorio destino $DEST_DIR no existe."
    exit 1
fi

# Copiar el archivo al destino
cp -v "$SRC_FILE" "$DEST_DIR"/

echo "¡Archivo copiado correctamente!"
