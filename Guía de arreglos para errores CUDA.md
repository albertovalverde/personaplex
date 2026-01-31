# Guía de arreglos para errores CUDA / cuDNN en Personaplex

Este documento resume los pasos que resolvieron los errores encontrados al ejecutar **moshi-personaplex** con GPU (CUDA), incluyendo:

- `The NVIDIA driver on your system is too old`
- `CUDNN_STATUS_NOT_INITIALIZED`

Está pensado para poder **repetir la instalación sin errores** o compartirla con otra persona.

---

## 1. Problema principal

El entorno tenía una **mezcla incompatible** de:

- Driver NVIDIA antiguo (≈ CUDA 12.0–12.1)
- PyTorch compilado con **CUDA 13.0**
- cuDNN demasiado nuevo

Esto provoca que:
- CUDA parezca disponible
- pero cuDNN falle al inicializar durante operaciones como `conv1d`

---

## 2. Solución recomendada (estable y probada)

### 2.1 Eliminar completamente dependencias CUDA/NVIDIA

```bash
pip uninstall -y torch torchvision torchaudio triton \
  nvidia-cublas nvidia-cuda-runtime nvidia-cuda-nvrtc \
  nvidia-cuda-cupti nvidia-cudnn-cu13 nvidia-cufft \
  nvidia-curand nvidia-cusolver nvidia-cusparse \
  nvidia-nccl nvidia-nvtx nvidia-nvjitlink \
  nvidia-cufile nvidia-cusparselt-cu13 cuda-bindings cuda-pathfinder
```

---

### 2.2 Recrear el entorno virtual (muy recomendado)

```bash
deactivate
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install -U pip
```

Esto evita librerías "fantasma" que quedan tras cambios de versión.

---

### 2.3 Instalar versiones compatibles (CUDA 12.1)

```bash
pip install torch==2.4.1+cu121 torchvision==0.19.1+cu121 torchaudio==2.4.1+cu121 \
  --index-url https://download.pytorch.org/whl/cu121
```

Estas versiones:
- Son compatibles con drivers NVIDIA ~12040
- Cumplen los requisitos de `moshi-personaplex (<2.5)`

Luego:

```bash
pip install moshi-personaplex
```

---

## 3. Verificación obligatoria de CUDA + cuDNN

Antes de ejecutar moshi, comprobar que cuDNN funciona correctamente:

```bash
python - << 'EOF'
import torch
print("torch:", torch.__version__)
print("cuda:", torch.version.cuda)
print("cudnn:", torch.backends.cudnn.version())
print("cuda available:", torch.cuda.is_available())

x = torch.randn(1, 1, 1024, device="cuda")
w = torch.randn(1, 1, 3, device="cuda")
y = torch.nn.functional.conv1d(x, w)
print("conv1d OK")
EOF
```

Si este test falla, **moshi no funcionará**.

---

## 4. Último recurso: desactivar cuDNN

Si cuDNN sigue fallando pese a todo:

```bash
export TORCH_CUDNN_V8_API_DISABLED=1
export CUDNN_DISABLE=1
```

Esto reduce rendimiento, pero evita el crash.

---

## 5. Ejecución final

```bash
SSL_DIR=$(mktemp -d)
python -m moshi.server --ssl "$SSL_DIR"
```

---

## 6. Notas finales

- Evitar PyTorch con CUDA 13 salvo que el driver sea ≥ 550
- Mantener torch < 2.5 para compatibilidad con personaplex
- Ante errores raros: **recrear el venv** suele ahorrar horas

---

✔️ Documento generado a partir de una instalación real y depurada
