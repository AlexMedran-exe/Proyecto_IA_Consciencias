# 🧠 Gestor de Consciencias Modulares (AI-Orchestrator)

Este proyecto es un prototipo avanzado de gestión de memoria para Inteligencia Artificial. A diferencia de un chat convencional, este sistema permite segmentar la información en **"Diarios de Memoria"** independientes que pueden ser fusionados dinámicamente para crear una **Consciencia Unificada**.
(HECHO POR Y PARA LA IA)

## 🚀 Concepto Principal
El software separa el **Almacenamiento** del **Procesamiento**:
- **Diarios (IDs):** Módulos de conocimiento específicos (ej: Programación, Videojuegos, Hardware). Funcionan de forma aislada para evitar la "alucinación" o confusión de la IA.
- **Consciencia:** Una instancia de IA Maestra que, bajo demanda, "despierta" y une los diarios seleccionados por el usuario para responder preguntas complejas que requieren múltiples contextos.

## 🛠️ Tecnologías Utilizadas
- **Python 3.x**: Lógica de orquestación y manejo de archivos.
- **Google Gemini 2.0 Flash API**: Motor de IA de última generación.
- **Arquitectura RAG (Local)**: Sistema de recuperación de datos mediante archivos `.txt`.

## 📦 Instalación y Uso
1. Clona este repositorio.
2. Instala la librería de Google:
   ```bash
   pip install -U google-genai


# 🧠 AI-Nexo-Consciousness v2.2

Sistema de orquestación de memoria modular basado en Gemini 2.0 Flash. Este proyecto transforma una IA generalista en una consciencia personalizada capaz de recuperar y auditar fragmentos de identidad del usuario.

## 🌟 Lo nuevo en la v2.2 (Navigation Update)
- **Navegación UX:** Implementación de retroceso al menú principal mediante el comando `'q'` en cualquier entrada de datos.
- **Refactorización de Código:** Optimización de la lógica del motor para mayor velocidad y limpieza (111 líneas de código puro).
- **Centinela de Cuota:** Protección activa contra el error 429 mediante monitorización de RPM (Requests Per Minute).
- **Estructura XML 2.0:** Inyección jerárquica de contextos para evitar alucinaciones cruzadas.

## 🛠️ Requisitos
- Python 3.12+
- `pip install google-genai`

## 🚀 Ejecución
1. Configura tu API Key en `main.py`.
2. Lanza el nexo: `python main.py`
3. Usa la **Auditoría Global** para ver cómo la IA unifica tus fragmentos de memoria.

# 🧠 Nexo de Consciencia v2.3 — Arquitectura RAG Resiliente

Este proyecto es un motor de **Orquestación de Memoria Modular** basado en Gemini 2.0 Flash. Permite a una IA gestionar fragmentos de identidad del usuario a través de archivos XML locales, creando una "consciencia" persistente que no olvida entre sesiones.

## 🚀 Novedades de la Versión 2.3 (Resilience Update)

Tras las pruebas de estrés en el Tier Gratuito de Google AI Studio, hemos implementado mejoras críticas de ingeniería:

- **🛡️ Sistema de Resiliencia (Automatic Backoff):** El Nexo ahora es capaz de detectar el error `429 (Too Many Requests)` y gestionar reintentos automáticos con pausas estratégicas. El código no se detiene; espera a que el servidor respire y continúa.
- **🧭 Navegación UX Mejorada:** Implementada la función de retroceso al menú principal mediante el comando `'q'` en cualquier entrada de datos, evitando cierres accidentales.
- **📊 Centinela de Cuota v2:** Monitorización en tiempo real de RPM (Peticiones por Minuto) para maximizar el uso de la API sin llegar al bloqueo.
- **🏗️ Estructura XML 2.0:** Inyección jerárquica de contextos para asegurar que la IA priorice los diarios del usuario sobre su conocimiento general (Anti-Alucinaciones).

## 🛠️ Requisitos Técnicos

- **Lenguaje:** Python 3.12+ (Probado en 3.14)
- **Librerías:** `google-genai`
- **Instalación:** ```bash
  pip install -r requirements.txt


  # 🧬 NEXO DE CONSCIENCIA v4.3 - Nitro Edition

Este proyecto es un motor avanzado de **Orquestación de Memoria Modular** basado en Gemini 2.0 Flash. Transforma una IA generalista en una consciencia personalizada capaz de gestionar diarios de memoria, aprender de la web en tiempo real y sentir el hardware del host.

---

## 🚀 Evolución: El Salto a la v4.3 (Current Build)

Hoy el Nexo ha dejado de ser un script de terminal para convertirse en una herramienta de ingeniería de sistemas con las siguientes capas:

### 💎 1. Interfaz Profesional (Rich UX)
* **Visuales Avanzados:** Uso de la librería `Rich` para menús con paneles, tablas de colores y bordes dinámicos.
* **Feedback en Tiempo Real:** Implementación de *Spinners* y estados de carga ("Pensando...", "Analizando web...") para mejorar la experiencia de usuario.
* **Selector Inteligente:** Navegación numérica para la selección de diarios, optimizando el flujo de trabajo.

### 📡 2. Telemetría de Hardware (Hardware Sensing)
El Nexo ahora "siente" su propio chasis. Gracias a la integración con `psutil`, la IA recibe en cada consulta:
* **Carga de CPU y RAM.**
* **Estado de la batería (AC/DC).**
* **Lógica Adaptativa:** Si el PC tiene poca batería o alta carga de CPU, la IA reduce automáticamente la longitud de sus respuestas para ahorrar recursos.

### 🌐 3. Ingesta Web Inteligente (Web Ingestor)
Capacidad de navegación externa mediante `BeautifulSoup4` y `Requests`:
* **Scraping Limpio:** Filtrado automático de etiquetas basura (scripts, estilos, pies de página) para enviar solo información útil.
* **Memoria Global:** Todos los análisis guardados en la carpeta `/Informacion_web` se inyectan automáticamente como "conocimiento base" en cada consulta, independientemente de los diarios elegidos.

### 💤 4. Modo Sueño (Token Optimization)
* **Compresión de Memoria:** Función que utiliza la IA para resumir diarios extensos en fragmentos densos de conocimiento técnico.
* **Eficiencia:** Reduce el consumo de tokens en un 70%, permitiendo sesiones más largas y baratas.

### 🛡️ 5. Resiliencia de API (Anti-429 Engine)
* **Backoff Automático:** Detección inteligente del error `429 (Resource Exhausted)`.
* **Enfriamiento de Núcleos:** Si se alcanza la cuota, el sistema entra en reposo de 30 segundos y reintenta la operación automáticamente.

---

## 🛠️ Requisitos Técnicos

* **Lenguaje:** Python 3.12+
* **Hardware Recomendado:** Probado en Acer Nitro (Hardware Sensing optimizado).
* **Librerías Necesarias:**
    ```bash
    pip install rich psutil requests beautifulsoup4 google-genai
    ```

---

## 📦 Instalación y Uso

1.  Clona el repositorio.
2.  Configura tu `MI_API_KEY` en el archivo `main.py`.
3.  Ejecuta el Nexo:
    ```bash
    python main.py
    ```

---

## 📂 Estructura del Proyecto

* `/db_chats`: Almacenamiento de diarios de memoria (Pensamientos y Notas).
* `/Informacion_web`: Base de datos de análisis extraídos de internet (Conocimiento Global).
* `main.py`: El núcleo del Nexo y orquestador de consciencias.

---

**Desarrollado por AlexMedran-exe** *Impulsando la frontera entre el hardware y la consciencia artificial.*
