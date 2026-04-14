## 🧬 Evolución del Nexo: De la Nube al Hardware

El proyecto ha pasado de ser un script dependiente de APIs externas a convertirse en un ecosistema de ingeniería local.Esta transición marca el paso de la dependencia de terceros hacia la **Soberanía Digital** y el aprovechamiento total del hardware del host.

| Versión | Hito Clave | Avance Tecnológico |
| :--- | :--- | :--- |
| **v1.2 (Prototipo)** | **El Origen** | Orquestación básica de memoria con archivos `.txt` y motor Google Gemini 2.0 Flash. |
| **v2.2 / v2.3** | **Resiliencia** | Gestión de errores 429 (Too Many Requests), centinela de cuota y navegación UX con el comando `'q'`. |
| **v4.3 (Nitro Edition)** | **Simbiosis** | Telemetría con `psutil` para sentir el hardware (CPU/RAM/Batería) e ingesta web con `BeautifulSoup4`. |
| **v7.1 (Current)** | **Independencia** | **Salto a Ollama (Llama 3.1/3.2)**.Procesamiento 100% local, visión artificial, búsqueda BM25 y dashboard en Streamlit . |

### 🚀 Por qué el salto al Procesamiento Local
**Privacidad Total:** Cero conexiones externas. Tus diarios y documentos nunca salen de tu Acer Nitro.
**Aprovechamiento de GPU:** Uso intensivo de la **RTX 5060** para inferencia de Llama 3.1 en VRAM .
**Sin Límites:** Eliminación de cuotas de API y límites de tokens mediante el uso de modelos locales vía Ollama.
**Multimodalidad Nativa:** Ingesta de PDFs con `pymupdf` y análisis de imágenes con **Llama 3.2 Vision** integrado en el dashboard.


# 🧠 Nexo de Consciencia (VERSION ACTUAL 7.1)

> **IA local con memoria persistente entre conversaciones.**  
> Sin límites de tokens. Sin suscripciones. Sin que tus datos salgan de tu máquina.

---

## ¿Qué es esto?

Nexo de Consciencia es un sistema de IA local que resuelve el problema más frustrante de usar herramientas como ChatGPT o Claude: **la amnesia entre chats**.

Cada vez que abres una conversación nueva, la IA no sabe quién eres, en qué proyecto estás trabajando, ni qué decidiste la semana pasada. Tienes que reexplicarlo todo desde cero.

Nexo lo soluciona guardando el contexto de tus conversaciones como **diarios** y fusionándolos cuando los necesitas. Si hoy hablas de Java, mañana de un videojuego y pasado de parkour, puedes decirle al Nexo que fusione esos tres hilos y tendrás una IA que recuerda todo lo anterior como si hubiera estado en las tres conversaciones.

Todo corre en tu ordenador. El modelo es tuyo. Los datos son tuyos.

---

## Características principales

### 💬 Modo Chat
Conversación independiente sobre cualquier tema. El modelo responde con todo su conocimiento (Llama 3.1) más las memorias relevantes que encuentre automáticamente. Al terminar, puedes guardar el chat como diario para uso futuro.

### 🧬 Modo Nexo
Seleccionas qué diarios quieres fusionar y el modelo recibe el contexto combinado de todos ellos. Es la implementación directa del concepto central: **coser diferentes hilos de conversación** para que la IA los procese como uno solo.

### 📎 Ingesta de Documentos
- **PDFs nativos** — Extrae el texto automáticamente, lo divide en chunks inteligentes y lo indexa. Tus apuntes de clase, documentación técnica o papers quedan disponibles como contexto.
- **Imágenes y capturas** — El modelo de visión (Llama 3.2 Vision) analiza la imagen y genera una descripción textual que se guarda como diario. Capturas de errores, diagramas, apuntes escritos a mano.

### 🔍 Recuperación BM25
Sistema de búsqueda basado en el mismo algoritmo que usa Elasticsearch internamente. Con stemming en español, lo que significa que buscar "proyectos" encuentra diarios etiquetados con "proyecto", "proyectando" o cualquier forma de la misma raíz.

### 👤 Perfil de usuario persistente
El sistema aprende sobre ti con cada sesión. Nivel técnico, hardware, proyectos activos, temas frecuentes. Todo se actualiza automáticamente al cerrar cada sesión para que la IA sepa quién eres desde el primer mensaje de cada conversación.

### 🔒 Privacidad total
Cero conexiones externas durante el uso. Cero APIs de pago. Cero datos enviados a servidores de terceros. Todo corre en local mediante Ollama.

---

## Requisitos

### Hardware mínimo
| Componente | Mínimo | Recomendado |
|---|---|---|
| RAM | 16 GB | 32 GB |
| GPU VRAM | 6 GB | 8 GB+ |
| Almacenamiento | 20 GB libres | 40 GB+ |

> El proyecto fue desarrollado en un **Acer Nitro con RTX 5060 y 32 GB RAM DDR5**. Con ese hardware Llama 3.1 corre en VRAM sin problema.

### Software
- **Windows 10/11** (también funciona en Linux y Mac)
- **Python 3.11** — imprescindible esta versión concreta
- **Ollama** — servidor local de modelos de IA

---

## Instalación paso a paso

### 1. Instalar Python 3.11

Descarga desde [python.org](https://www.python.org/downloads/release/python-3119/) el instalador de 64 bits para Windows. Durante la instalación marca **"Add Python to PATH"**.

Verifica:
```powershell
py -3.11 --version
# Debe mostrar: Python 3.11.x
```

### 2. Instalar Ollama

Descarga desde [ollama.com](https://ollama.com) e instala normalmente. Luego descarga los modelos necesarios:

```powershell
# Modelo principal para chat (imprescindible)
ollama pull llama3.1

# Modelo de visión para imágenes (opcional, 7GB)
ollama pull llama3.2-vision
```

Verifica que Ollama funciona:
```powershell
ollama list
# Debe mostrar los modelos descargados
```

### 3. Instalar dependencias de Python

```powershell
py -3.11 -m pip install psutil requests rank_bm25 nltk streamlit pymupdf
```

### 4. Configurar NLTK (una sola vez)

```powershell
cd C:\ruta\a\tu\proyecto
py -3.11 nexo_consciencia_v6_2.py --setup
```

### 5. Verificar la instalación

```powershell
py -3.11 -m py_compile nexo_consciencia_v6_2.py
py -3.11 -m py_compile nexo_dashboard_v7_1.py
# Si no aparece ningún error, todo está correcto
```

---

## Arranque

### Opción A — Automático (recomendado)

Haz doble clic en `iniciar_nexo.bat`. El script hace todo automáticamente:
1. Verifica que Ollama está corriendo (lo inicia si no)
2. Arranca el servidor Streamlit
3. Abre la interfaz en el navegador

> La primera vez que lo uses, edita `iniciar_nexo.bat` con el Bloc de Notas y revisa que las rutas de la sección `CONFIGURACION` sean correctas para tu sistema.

### Opción B — Manual

```powershell
# Terminal 1: asegúrate de que Ollama está corriendo
ollama serve

# Terminal 2: arranca el dashboard
cd C:\ruta\a\tu\proyecto
py -3.11 -m streamlit run nexo_dashboard_v7_1.py
```

Luego abre `http://localhost:8501` en el navegador.

---

## Estructura de archivos

```
Proyecto_IA_Consciencias/
│
├── nexo_consciencia_v6_2.py    # Motor principal (backend)
├── nexo_dashboard_v7_1.py      # Interfaz web (Streamlit)
├── iniciar_nexo.bat            # Lanzador automático
│
├── perfil_usuario.json         # Tu perfil (se crea automáticamente)
├── nexo_audit.log              # Log de todas las operaciones
│
└── db_consciencias/            # Base de datos de memorias
    ├── chat_java.md            # Ejemplo: chat guardado
    ├── chat_java.json          # Metadatos e índice BM25
    ├── apuntes_p01.md          # Ejemplo: chunk de PDF
    ├── apuntes_p01.json
    └── sesion_20260412.md      # Ejemplo: resumen automático de sesión
```

> **Nunca borres `db_consciencias/` manualmente** a menos que quieras borrar toda la memoria del sistema. Si un archivo se corrompe, usa la función `:reparar` desde el CLI o el dashboard.

---

## Cómo funciona por dentro

### El ciclo completo de memoria

```
Conversación nueva
       │
       ▼
  Modo Chat ──► Guardas el chat como diario
       │                    │
       │                    ▼
       │           db_consciencias/
       │           (MD + JSON indexado)
       │                    │
       ▼                    ▼
  Modo Nexo ◄── Seleccionas qué diarios fusionar
       │
       ▼
  Contexto fusionado → Llama 3.1 → Respuesta con memoria
```

### BM25 con stemming

Cuando escribes una pregunta en el chat, el sistema busca automáticamente en todos los diarios usando BM25 (el algoritmo de Elasticsearch) con SnowballStemmer en español. Esto significa que:

- Buscar `"proyectos"` encuentra diarios con el tag `"proyecto"`
- Buscar `"conversaciones"` encuentra `"conversacion"`
- Buscar `"aprendiendo"` encuentra `"aprender"`

El resultado más relevante se inyecta en el prompt antes de que el modelo responda.

### Boot context

Al inicio de cada prompt el sistema inyecta automáticamente:
- Tu perfil completo (nombre, hardware, nivel técnico, proyectos)
- Las memorias más relevantes para tu pregunta actual
- El historial de los últimos 6 turnos de la sesión

Esto hace que la IA sepa quién eres y en qué estás trabajando **desde el primer mensaje**, sin que tengas que explicarlo.

### Resúmenes automáticos de sesión

Cuando cierras una sesión (botón "Guardar sesión" en el dashboard), el propio modelo genera un resumen estructurado:

```
TEMAS: python, bm25, arquitectura rag
DECISIONES: usar chunking de 1500 palabras con overlap de 200
PENDIENTE: implementar pynvml para telemetría VRAM
USUARIO_INFO: nivel python intermedio, RTX 5060, proyecto nexo
SINOPSIS: Se discutió la arquitectura de recuperación...
```

Este resumen se indexa como cualquier otro diario. En futuras sesiones, BM25 puede recuperarlo automáticamente cuando la conversación toque temas relacionados.

---

## Guía de uso del dashboard

### Sidebar (barra lateral)

| Elemento | Función |
|---|---|
| `💬 Chat` / `🧬 Nexo` | Cambia entre los dos modos |
| Checkboxes de diarios | Marca qué contexto incluir en Modo Nexo |
| `▼ 💬 Chats` | Sección colapsable de chats guardados |
| `▼ 📄 PDFs` | Sección colapsable de PDFs ingestados |
| `▼ 🖼️ Imágenes` | Sección colapsable de imágenes analizadas |
| `✓ All` | Marca o desmarca todos los del grupo de golpe |
| `💾 Guardar sesión` | Genera resumen y guarda la conversación actual |

### Pestañas principales

**💬 Chat** — Conversación independiente. Sin contexto de otros diarios a menos que BM25 encuentre algo relevante automáticamente. Al terminar, guarda el chat con un nombre y tags.

**🧬 Nexo** — Conversación con el contexto que hayas seleccionado en el sidebar. Cuantos más diarios marques, más contexto tiene el modelo.

**📎 Documentos** — Sube PDFs o imágenes para convertirlos en diarios. Los PDFs se dividen en chunks automáticamente. Las imágenes se describen con Llama 3.2 Vision.

**📂 Diarios** — Gestión completa. Ver, crear manualmente, y explorar todo lo que hay en `db_consciencias/`.

**📋 Sesiones** — Historial de todas las sesiones guardadas con sus resúmenes estructurados.

---

## Uso típico

### Escenario 1: Guardar una conversación de Java para usarla después

1. Abre la pestaña **💬 Chat**
2. Habla de tus dudas de Java con normalidad
3. Al terminar, escribe un nombre (`java_herencia`) y tags (`java, universidad`)
4. Pulsa **Guardar diario**
5. En futuras sesiones, marca `java_herencia` en el sidebar y abre **🧬 Nexo**

### Escenario 2: Fusionar varios chats en el Nexo

1. Tienes guardados: `java_tareas`, `videojuego_mecanicas`, `parkour_tecnicas`
2. En el sidebar, marca ☑ `videojuego_mecanicas` y ☑ `parkour_tecnicas`
3. Abre **🧬 Nexo**
4. El modelo tiene acceso a ambas conversaciones como si hubiera participado en las dos

### Escenario 3: Ingestar apuntes de clase en PDF

1. Abre **📎 Documentos** → **📄 PDF**
2. Sube el PDF
3. Pon nombre (`apuntes_java_tema3`) y tags (`java, universidad, teoria`)
4. Ajusta el tamaño de chunk si quieres (1500 palabras por defecto)
5. Pulsa **Procesar e ingestar**
6. Aparecen `apuntes_java_tema3_p01`, `apuntes_java_tema3_p02`... en la Biblioteca
7. Marca todos con **✓ All** y úsalos en Modo Nexo

### Escenario 4: Analizar un error con captura de pantalla

1. Abre **📎 Documentos** → **🖼️ Imagen**
2. Sube la captura del error
3. En "Instrucción para el modelo" escribe: `¿Qué error muestra esta captura y cómo se soluciona?`
4. Pulsa **Analizar imagen con IA**
5. La descripción y solución se guardan como diario para futuras consultas

---

## CLI (modo consola)

Si prefieres usar el Nexo sin interfaz web, puedes usar el CLI directamente:

```powershell
py -3.11 nexo_consciencia_v6_2.py
```

Comandos disponibles dentro del CLI:

| Comando | Función |
|---|---|
| `:ayuda` | Lista todos los comandos |
| `:perfil` | Ver tu perfil actual |
| `:perfil set nombre Alex` | Actualizar un campo del perfil |
| `:memorias` | Listar todas las memorias guardadas |
| `:guardar ID` | Guardar texto como nueva memoria |
| `:buscar TEXTO` | Buscar memorias relevantes con BM25 |
| `:reparar` | Verificar integridad de la base de datos |
| `:salir` | Cerrar sesión y generar resumen automático |
| `:salir-rapido` | Salir sin guardar |

---

## Solución de problemas frecuentes

**`SyntaxError: source code string cannot contain null bytes`**  
El archivo tiene bytes corruptos por cómo fue copiado. Solución:
```powershell
python -c "
data = open('nexo_dashboard_v7_1.py','rb').read()
open('nexo_dashboard_v7_1.py','wb').write(data.replace(b'\x00',b''))
"
```

**`Ollama no responde`**  
Abre una terminal y ejecuta `ollama serve`. Déjala abierta mientras usas el Nexo.

**`llama3.2-vision no está instalado`**  
```powershell
ollama pull llama3.2-vision
```
Pesa aproximadamente 7 GB. Tu modelo `llama3.1` se queda intacto.

**`pymupdf no está instalado`** (PDFs no funcionan)  
```powershell
py -3.11 -m pip install pymupdf
```

**El dashboard no arranca con `streamlit run`**  
Usa siempre `py -3.11 -m streamlit run` en lugar de `streamlit run` directamente. En Windows, `streamlit` solo funciona como módulo de Python si no está en el PATH.

**Streamlit incompatible** (Python 3.14)  
Este proyecto requiere **Python 3.11**. Python 3.14 tiene incompatibilidades conocidas con Streamlit. Instala Python 3.11 desde [python.org](https://www.python.org/downloads/release/python-3119/) y úsalo con `py -3.11`.

---

## Stack tecnológico

| Componente | Tecnología | Función |
|---|---|---|
| Modelo de chat | Llama 3.1 (via Ollama) | Inferencia principal |
| Modelo de visión | Llama 3.2 Vision (via Ollama) | Análisis de imágenes |
| Servidor de modelos | Ollama | Gestión local de LLMs |
| Interfaz web | Streamlit | Dashboard visual |
| Búsqueda | BM25Okapi + SnowballStemmer | Recuperación de memorias |
| Extracción PDF | pymupdf (fitz) | Ingesta de documentos |
| Telemetría | psutil | Monitorización de hardware |
| Almacenamiento | Archivos MD + JSON | Base de datos de memorias |
| Lenguaje | Python 3.11 | Backend completo |

---

## Diferencias con soluciones similares

| | Nexo | NotebookLM | ChatGPT Memory | Mem.ai |
|---|---|---|---|---|
| Conocimiento general | ✅ Completo | ❌ Solo tus docs | ✅ | ✅ |
| Memoria personal | ✅ | ✅ | ✅ Limitada | ✅ |
| Privacidad total | ✅ 100% local | ❌ Google servers | ❌ OpenAI servers | ❌ Cloud |
| Coste operativo | ✅ Cero | ❌ Suscripción | ❌ Suscripción | ❌ Suscripción |
| Control del contexto | ✅ Manual y automático | ❌ Automático | ❌ Automático | ❌ Automático |
| Funciona sin internet | ✅ | ❌ | ❌ | ❌ |

La diferencia clave con NotebookLM (el competidor más parecido): NotebookLM es RAG puro, sin documentos no sabe nada. Nexo tiene el conocimiento completo de Llama 3.1 más tus memorias personales como contexto adicional.

---

## Roadmap

- [ ] Telemetría VRAM con `pynvml` para GPUs NVIDIA
- [ ] Importación masiva de chats antiguos desde carpetas
- [ ] Soporte OCR para PDFs escaneados sin texto seleccionable
- [ ] API REST para integración con otras herramientas
- [ ] Instalador automático en un solo clic

---

## Créditos

**Idea y desarrollo:** AlexMedran-exe  
**Arquitectura de seguridad y backend:** Claude (Anthropic)  
**Compatibilidad Windows y fix amnesia:** Gemini (Google)  
**Modelos de IA:** Meta (Llama 3.1 y Llama 3.2 Vision) via Ollama

---

*Proyecto iniciado en clase, desarrollado con curiosidad.*
