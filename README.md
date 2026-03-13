# 🧠 Gestor de Consciencias Modulares (AI-Orchestrator)

Este proyecto es un prototipo avanzado de gestión de memoria para Inteligencia Artificial. A diferencia de un chat convencional, este sistema permite segmentar la información en **"Diarios de Memoria"** independientes que pueden ser fusionados dinámicamente para crear una **Consciencia Unificada**.

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
