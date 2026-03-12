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
