# Guía de Desarrollo Pepper (Híbrido) - Integración PersonaPlex & OM1

Esta guía detalla la arquitectura, configuración y el puente Zenoh necesario para integrar el modelo de voz **PersonaPlex (Moshi)** con el sistema operativo robótico **OM1** para el robot Pepper.

---

## 1. Arquitectura del Sistema Híbrido

La integración se basa en un diseño desacoplado donde OM1 maneja la percepción/acción y PersonaPlex se encarga de la generación de voz fluida y natural.

### Componentes:
*   **OM1 (Cerebro Lógico)**: Ejecuta el razonamiento profundo (OpenAI/Gemini) y gestiona los sensores del robot.
*   **PersonaPlex (Cerebro Emocional/Conversacional)**: Proporciona respuestas de baja latencia (<200ms) para charla trivial y verbaliza las respuestas del sistema lógico.
*   **Zenoh (Bus de Comunicación)**: El "sistema nervioso" que transporta audio y comandos de control entre ambos repositorios.

---

## 2. Instalación y Requisitos

### En el repositorio PersonaPlex:
Asegúrate de tener instalada la librería de Zenoh y las dependencias de Moshi:

```bash
# Instalación de dependencias
./venv/bin/pip install eclipse-zenoh
```

El archivo `moshi/requirements.txt` debe incluir:
```text
eclipse-zenoh
```

---

## 3. El Puente Zenoh (`scripts/zenoh_bridge.py`)

Este script es el corazón de la integración en el lado de PersonaPlex. Sus funciones principales son:

1.  **Escuchar el Micrófono**: Se suscribe al tópico `pepper/audio/mic` para recibir audio en tiempo real desde OM1.
2.  **Procesar Audio**: Envía los frames de audio al modelo Moshi/Mimi.
3.  **Hablar**: Publica el audio generado por el agente en `pepper/audio/speaker`.
4.  **Control**: Escucha comandos en `pepper/personaplex/control` para inyectar texto o prompts dinámicos.

### Lanzamiento Automatizado (Recomendado)

He creado un script que configura todo automáticamente (limpieza de procesos, variables de entorno, certificados y logs). Es la forma más fácil de empezar:

```bash
# Dar permisos (solo la primera vez)
chmod +x scripts/start_pepper.sh

# Ejecutar el sistema completo
./scripts/start_pepper.sh
```

---

### Lanzamiento Manual (Avanzado)

Si necesitas control total o depuración en vivo, puedes lanzar los componentes por separado:

#### 1. Servidor (Moshi + Zenoh)
Copia y pega este bloque completo:

```bash
export HF_TOKEN="tu_token_aqui" && \
export REQUESTS_CA_BUNDLE="/etc/ssl/certs/ca-certificates.crt" && \
SSL_DIR=$(mktemp -d) && \
PYTHONPATH=moshi ./venv/bin/python -m moshi.server \
    --ssl "$SSL_DIR" \
    --voice-prompt-dir ./voices \
    --static client/dist \
    --zenoh \
    --port 8998
```

> [!WARNING]
> El flag `--ssl` requiere un argumento (el directorio donde se guardarán los certificados). Si lanzas el comando manualmente, asegúrate de definir primero la variable `SSL_DIR` como en el ejemplo de arriba. No ejecutes `--ssl` solo.

---

## 4. Tópicos Zenoh de Integración

| Tópico | Dirección (desde PersonaPlex) | Descripción |
| :--- | :--- | :--- |
| `pepper/audio/mic` | Entrada (Subscriber) | Audio crudo del micrófono del robot. |
| `pepper/audio/transcription` | Salida (Publisher) | **Tiempo real**: Texto transcrito por Moshi enviado a OM1. |
| `pepper/audio/speaker` | Salida (Publisher) | Audio generado por Moshi para los altavoces. |
| `pepper/personaplex/control` | Entrada (Subscriber) | Comandos de control e inyección de texto desde OM1. |

---

## 5. Visualización en Tiempo Real (WebSim)

El simulador de OM1 (puerto `8005`) ha sido optimizado para mostrar feedback instantáneo:

*   **UI Desacoplada**: El historial de entrada ("Input History") se actualiza cada 0.5s leyendo directamente del bus Zenoh. No depende de que el cerebro termine de procesar.
*   **Transparencia**: Puedes ver las palabras aparecer en el simulador mientras el usuario habla en la interfaz web de Moshi.

---

## 6. Flujo de Trabajo para Demos

Para una ejecución exitosa de la demo híbrida de Pepper:

1.  **Iniciar OM1**: Ejecuta `python src/run.py pepper`.
2.  **Iniciar PersonaPlex**: Ejecuta el servidor con el flag `--zenoh`.
3.  **Verificación**:
    *   Abre `https://localhost:8998` para hablar.
    *   Abre `http://localhost:8005` para ver la visualización de Pepper.
    *   Verás el texto de tu voz aparecer instantáneamente en el "Input History".

---

## 7. Notas de Desarrollo y Estrategia

*   **Barge-in**: PersonaPlex soporta interrupciones naturales. Si el usuario habla mientras Pepper responde, el modelo detectará la interrupción automáticamente.
*   **Loop de Cortex**: El núcleo de OM1 está configurado para no bloquearse. Si una respuesta del LLM es lenta, el robot sigue refrescando su estado y visualización.
*   **Voz de Pepper**: El archivo `voices/pepper.pt` es crítico para mantener la identidad sonora del robot.

## 7. Resolución de Problemas (Troubleshooting)

### Error: CUDA Out of Memory
Si al lanzar el servidor obtienes un error de memoria (OOM), es probable que haya procesos antiguos bloqueando la GPU. Usa este comando para limpiar la memoria:

```bash
pkill -9 -f "moshi|zenoh_bridge"
```

### Error de JavaScript: `addModule` en la Web
Si ves un error de JavaScript o el micro no se activa, asegúrate de estar accediendo por **HTTPS**. El navegador bloquea las APIs de audio en conexiones inseguras (HTTP).

---

> [!IMPORTANT]
> Esta arquitectura permite actualizar OM1 de forma independiente sin afectar la lógica específica de audio y voz que reside en este repositorio PersonaPlex.
