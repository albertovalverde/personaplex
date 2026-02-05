# Guía Técnica de Desarrollo e Integración (Pepper 2026)

Este documento detalla los componentes internos y flujos de datos para desarrolladores que quieran extender el sistema.

## 1. Topología de Red

```
[ PEPPER ROBOT ]              [ SERVIDOR / BRIDGE ]               [ CEREBRO / MOSHI ]
(Python 2.7)                  (Python 3.10)                       (Python 3.10 + GPU)
      |                             |                                   |
  Mic | --(Raw TCP 9001)-->  [Socket Server] --(Zenoh Pub)-->  [Zenoh Sub: pepper/audio/mic]
      |                             |                                   |
Spkr | <--(Raw TCP 9001)--  [Socket Server] <--(Zenoh Sub)--  [Zenoh Pub: pepper/audio/speaker]
      |                             |                                   |
 Video | --(Raw TCP 9002)-->  [Socket Server] --(Zenoh Pub)-->  [Zenoh Sub: pepper/vision/camera]
      |                             |                                   |
Motion | <--(Raw TCP 9003)--  [Socket Server] <--(Zenoh Sub)--  [Zenoh Pub: pepper/control]
```

## 2. Componentes Críticos

### A. Moshi Server (`moshi/server.py`)
Se ha modificado el servidor original de Kyutai para:
1.  **Suscribirse a Zenoh**: Escucha `pepper/audio/mic`.
2.  **Inyección Directa**: Los paquetes de audio se inyectan en `active_pcm_queue`.
3.  **Corrección de Forma**: Se aplica `all_pcm_data.reshape(-1)` y `chunk.to(device)` para evitar errores de tensores 4D o de CPU/GPU.
4.  **Publicación**: El audio generado se envía a `pepper/audio/speaker`.

### B. El Puente (`scripts/pepper_socket_bridge.py`)
Es el componente más estable. Simplemente mueve bytes de izquierda a derecha.
*   **Audio**: Full-duplex en puerto 9001.
*   **Video**: Unidireccional en puerto 9002 (Framing con cabecera de 4 bytes para tamaño).
*   **Control**: JSON Lines en puerto 9003.

### C. Cliente Headless (`scripts/headless_moshi_client.py`)
Mantiene vivo el WebSocket de inferencia. Es cruicial en producción porque Moshi no procesa audio si no hay un cliente "Web" conectado. Este script simula ser ese cliente.

## 3. Protocolos

### Audio
*   **Formato**: PCM 16-bit, Monocanal.
*   **Sample Rate**: 16000Hz (Robot) <-> Bridge <-> 24000Hz (Moshi). *Nota: Actualmente se inyecta directo, la conversión de SR la maneja la tolerancia del modelo o flags de ffmpeg en el simulador.*

### Video
*   **Formato**: MJPEG (Secuencia de imágenes JPEG).
*   **Transporte**: `[4 bytes Size (Big Endian)] + [JPEG Bytes]`.

### Control
*   **Formato**: JSON Lines (`\n`).
*   **Schema**: `{"action": "say", "text": "..."}` o `{"action": "move", "x": 1.0}`.

## 4. Solución de Problemas (Troubleshooting)

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| **Error `RuntimeError: devices cpu and cuda:0`** | Falta mover tensores a GPU. | Verificar `chunk.to(device)` en `server.py`. (Ya parcheado) |
| **Error `Shape mismatch [1,1,1,T]`** | Tensores no aplanados. | Verificar `reshape(-1)` en `server.py`. (Ya parcheado) |
| **"Socket not connected" en logs web** | Conflicto Headless/Web. | Cerrar `headless_moshi_client.py` si usas Web, o viceversa. |
| **Robot no habla** | Falta sesión activa. | Asegurar que Web UI o Headless Client están corriendo. |

## 5. Futuras Mejoras
*   Implementar re-sampling real de alta calidad (SoX) en el Bridge.
*   Añadir compresión Opus en el tramo Robot->Bridge para redes lentas.
*   Integrar OM1 (Llama 3) para la toma de decisiones basada en el topic `pepper/audio/transcription`.
