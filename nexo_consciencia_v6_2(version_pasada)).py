"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        NEXO DE CONSCIENCIA v6.2 — WINDOWS EDITION (Vision Ready)           ║
║        Autor original  : AlexMedran-exe                                    ║
║        Arquitectura    : Claude (Anthropic)                                ║
║        Fix Windows     : Gemini (detectó bug amnesia + compatibilidad)     ║
║                                                                              ║
║  CHANGELOG v6.2 (respecto a v6.0 y v6.1):                                  ║
║    ✅ Compatibilidad Windows: sin fcntl, escritura atómica con .tmp         ║
║    ✅ Fix bug amnesia de Gemini integrado (historial real en .md)            ║
║    ✅ Seguridad v6.0 restaurada (path traversal, JSON corrupto, rate limit) ║
║    ✅ BM25 con SnowballStemmer restaurado (perdido en v6.1)                 ║
║    ✅ Prompt condicional: diferente si hay contexto o no (fix v6.1)         ║
║    ✅ Resúmenes automáticos al cerrar sesión (perdido en v6.1)              ║
║    ✅ Boot context y perfil de usuario (perdido en v6.1)                    ║
║    ✅ Fix score negativo BM25 con corpus pequeño (bug detectado en tests)   ║
║    ✅ Vision ready: _llamar_ollama_vision + MODELO_VISION en CONFIG          ║
║    ✅ MAX_CONTENT_BYTES ampliado a 200KB para PDFs e imágenes                ║
╚══════════════════════════════════════════════════════════════════════════════╝

INSTALACIÓN (ejecutar una sola vez):
    pip install psutil requests rank_bm25 nltk

PRIMERA EJECUCIÓN:
    python nexo_consciencia_v6_2.py --setup

USO NORMAL:
    python nexo_consciencia_v6_2.py

REQUISITOS:
    - Ollama corriendo: ollama serve
    - Modelo descargado: ollama pull llama3.1
    - Python 3.9+
    - Windows 10/11 o Linux/Mac
"""

# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTS
# ══════════════════════════════════════════════════════════════════════════════

import os
import re
import sys
import json
import time
import logging
import hashlib
import datetime
import argparse
import textwrap

# ── Compatibilidad Windows/Linux para bloqueo de archivos ────────────────────
# fcntl solo existe en Linux/Mac. En Windows usamos escritura atómica (.tmp +
# os.replace) que es suficiente para el caso de uso de un solo proceso.
# Si en el futuro añades hilos o multiproceso en Windows, necesitarás
# 'portalocker' (pip install portalocker) como sustituto de fcntl.
IS_WINDOWS = sys.platform == "win32"
if not IS_WINDOWS:
    import fcntl  # Solo en Linux/Mac

# ── Librerías de terceros ────────────────────────────────────────────────────
_missing = []
try:
    import psutil
except ImportError:
    _missing.append("psutil")

try:
    import requests
except ImportError:
    _missing.append("requests")

try:
    from rank_bm25 import BM25Okapi
    BM25_OK = True
except ImportError:
    BM25_OK = False
    print("⚠️  rank_bm25 no instalado. Búsqueda degradada a keyword básico.")
    print("   Instalar: pip install rank_bm25\n")

try:
    from nltk.stem.snowball import SnowballStemmer
    STEMMER = SnowballStemmer("spanish")
    NLTK_OK = True
except ImportError:
    STEMMER = None
    NLTK_OK = False
    print("⚠️  nltk no instalado. Sin normalización morfológica en español.")
    print("   Instalar: pip install nltk  → luego ejecutar --setup\n")

if _missing:
    sys.exit(f"❌ Librerías faltantes: {_missing}\n   Ejecuta: pip install {' '.join(_missing)}")


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

CONFIG = {
    # Rutas
    "DB_PATH":            "db_consciencias",
    "PERFIL_PATH":        "perfil_usuario.json",
    "AUDIT_LOG":          "nexo_audit.log",

    # Ollama
    "OLLAMA_ENDPOINT":    "http://localhost:11434/api/generate",
    "OLLAMA_HEALTH":      "http://localhost:11434/api/tags",
    "MODELO_PRINCIPAL":   "llama3.1:latest",   # Ajustado para Windows (ollama list para verificar)
    "MODELO_VISION":      "llama3.2-vision:latest", # Para análisis de imágenes y capturas
    "TIMEOUT_INFERENCIA": 120,                  # Segundos. RTX 5060 debería ir rápido.

    # Seguridad
    "MAX_ID_LENGTH":      64,
    "MAX_QUERY_LENGTH":   2000,
    "MAX_CONTENT_BYTES":  200_000,             # 200KB por memoria (ampliado para PDFs e imágenes)
    "MAX_CONTEXT_CHARS":  12_000,              # Límite del prompt fusionado
    "MAX_IDS_FUSION":     10,
    "RATE_LIMIT_SEG":     3,
    "SNIPPET_LENGTH":     1000,                # v6.1 aumentó a 1000, lo mantenemos (mejor para BM25)

    # Comportamiento
    "HW_CACHE_SEG":       15,
    "CPU_UMBRAL_ALTO":    80,
    "ID_PATTERN":         re.compile(r'^[a-zA-Z0-9_\-]{1,64}$'),
}


# ══════════════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["AUDIT_LOG"], encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NexoV6_2")


# ══════════════════════════════════════════════════════════════════════════════
#  UTILIDAD: ESCRITURA ATÓMICA (compatible Windows y Linux)
# ══════════════════════════════════════════════════════════════════════════════

def escribir_atomico(path: str, contenido_str: str = None, contenido_dict: dict = None):
    """
    Escritura atómica multiplataforma.

    PROBLEMA QUE RESUELVE:
    Si escribimos directamente sobre el archivo y el proceso se interrumpe
    (Ctrl+C, corte de luz, crash de Python), el archivo queda corrupto:
    existe pero está vacío o incompleto. En la próxima ejecución, json.load()
    lanza una excepción y el sistema falla.

    SOLUCIÓN:
    1. Escribir en un archivo temporal (.tmp) en el mismo directorio
    2. Llamar os.replace() que es ATÓMICO en Windows y Linux:
       - Si falla antes del replace: el original queda intacto
       - Si falla durante el replace: el SO garantiza que uno de los dos queda válido
       - Si termina: el original es reemplazado por el nuevo contenido

    PARÁMETROS:
    - path: ruta del archivo final
    - contenido_str: string a escribir (para .md)
    - contenido_dict: dict a serializar como JSON (para .json)
    (exactamente uno de los dos debe estar definido)
    """
    if (contenido_str is None) == (contenido_dict is None):
        raise ValueError("Especifica exactamente uno: contenido_str O contenido_dict")

    path_tmp = path + ".tmp"
    try:
        with open(path_tmp, "w", encoding="utf-8") as f:
            if contenido_str is not None:
                f.write(contenido_str)
            else:
                json.dump(contenido_dict, f, indent=4, ensure_ascii=False)
        os.replace(path_tmp, path)  # Atómico en Windows y Linux
    except Exception as e:
        # Limpiar el .tmp si quedó huérfano
        if os.path.exists(path_tmp):
            try:
                os.remove(path_tmp)
            except OSError:
                pass
        raise IOError(f"Escritura atómica fallida en {path}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class NexoCompleto:
    """
    Motor central de Nexo de Consciencia v6.2.

    Combina lo mejor de v6.0 (seguridad, BM25+stemming, boot context,
    resúmenes automáticos) con los fixes de v6.1 (compatibilidad Windows,
    corrección del bug de amnesia, snippet de 1000 chars para BM25).
    """

    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), CONFIG["DB_PATH"])
        os.makedirs(self.db_path, exist_ok=True)

        self._hw_cache = ""
        self._hw_ts    = 0
        self._rl       = {}           # Rate limit: {cliente: timestamp}

        self.historial_sesion = []
        self.sesion_id        = datetime.datetime.now().strftime("sesion_%Y%m%d_%H%M%S")
        self.sesion_inicio    = datetime.datetime.now()

        logger.info(f"NexoCompleto v6.2 iniciado (Windows={IS_WINDOWS}) | Sesión: {self.sesion_id}")
        self._verificar_ollama()

    # ──────────────────────────────────────────────────────────────────────────
    #  SEGURIDAD Y VALIDACIÓN
    # ──────────────────────────────────────────────────────────────────────────

    def _validar_id(self, id_chat: str) -> str:
        """
        Previene Path Traversal.

        AUSENTE EN v6.1 — Gemini lo eliminó al simplificar el código.
        Restaurado en v6.2 porque es la protección más crítica del sistema.

        Sin esta función, guardar_memoria("../../windows/system32/drivers/etc/hosts", ...)
        escribiría fuera del directorio permitido.
        """
        if not isinstance(id_chat, str):
            raise ValueError("El ID debe ser texto.")
        if not CONFIG["ID_PATTERN"].match(id_chat):
            raise ValueError(
                f"ID inválido: '{id_chat}'. Solo letras, números, _ y -. "
                f"Máximo {CONFIG['MAX_ID_LENGTH']} caracteres."
            )
        # Segunda línea de defensa: verificar ruta absoluta
        ruta_obj  = os.path.realpath(os.path.join(self.db_path, id_chat))
        ruta_base = os.path.realpath(self.db_path)
        if not ruta_obj.startswith(ruta_base + os.sep):
            raise PermissionError(f"Intento de acceso fuera de db_path: {id_chat}")
        return id_chat

    def _validar_query(self, q: str) -> str:
        """Limpia y valida las consultas antes de inyectarlas en prompts."""
        if not isinstance(q, str) or not q.strip():
            raise ValueError("La consulta no puede estar vacía.")
        if len(q) > CONFIG["MAX_QUERY_LENGTH"]:
            raise ValueError(f"Consulta demasiado larga (máx. {CONFIG['MAX_QUERY_LENGTH']} chars).")
        # Eliminar caracteres de control (dejan el log ilegible y pueden confundir al modelo)
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', q).strip()

    def _check_rate_limit(self, cliente: str = "local"):
        """Evita saturación por consultas masivas. Imprescindible si expones API web."""
        ahora  = time.time()
        ultima = self._rl.get(cliente, 0)
        espera = ahora - ultima
        if espera < CONFIG["RATE_LIMIT_SEG"]:
            raise PermissionError(f"Rate limit: espera {CONFIG['RATE_LIMIT_SEG'] - espera:.1f}s.")
        self._rl[cliente] = ahora

    # ──────────────────────────────────────────────────────────────────────────
    #  HARDWARE TELEMETRÍA
    # ──────────────────────────────────────────────────────────────────────────

    def _get_hw(self) -> str:
        ahora = time.time()
        if ahora - self._hw_ts > CONFIG["HW_CACHE_SEG"]:
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                ram = psutil.virtual_memory().percent
                # En Windows con RTX 5060, psutil no lee VRAM directamente.
                # Para VRAM necesitarías 'pynvml' (pip install nvidia-ml-py).
                # Lo dejamos pendiente para no añadir dependencias ahora.
                bat = psutil.sensors_battery()
                bat_str = f"{bat.percent:.0f}%" if bat else "AC/Enchufado"
                self._hw_cache = f"CPU:{cpu}% RAM:{ram}% BAT:{bat_str}"
            except Exception as e:
                self._hw_cache = "HW:N/A"
                logger.warning(f"Error telemetría: {e}")
            self._hw_ts = ahora
        return self._hw_cache

    def _cpu_alta(self) -> bool:
        try:
            return psutil.cpu_percent(interval=0.1) > CONFIG["CPU_UMBRAL_ALTO"]
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────────────────────
    #  PERFIL DE USUARIO
    # ──────────────────────────────────────────────────────────────────────────

    def cargar_perfil(self) -> dict:
        """
        Carga el perfil con fusión defensiva.
        Si al JSON le falta algún campo nuevo, usa el valor del perfil_base.
        Esto evita KeyError cuando añadimos campos nuevos en futuras versiones.
        """
        perfil_base = {
            "nombre":                    "Alex",
            "hardware":                  "Acer Nitro (RTX 5060, 32GB RAM DDR5, Windows 11 Pro)",
            "nivel_python":              "intermedio (aprendiendo)",
            "nivel_otros":               {"Java": "básico"},
            "proyectos_activos":         ["nexo_consciencia"],
            "temas_frecuentes":          [],
            "preferencias_comunicacion": "respuestas directas y técnicas",
            "notas_personales":          "",
            "total_sesiones":            0,
            "ultima_sesion":             None,
            "version_perfil":            "6.2"
        }
        path = CONFIG["PERFIL_PATH"]
        if not os.path.exists(path):
            return perfil_base
        try:
            with open(path, "r", encoding="utf-8") as f:
                datos = json.load(f)
            perfil_base.update(datos)   # Los datos guardados sobreescriben los defaults
            return perfil_base
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error cargando perfil: {e}. Usando defaults.")
            return perfil_base

    def guardar_perfil(self, perfil: dict) -> None:
        """Guardado atómico del perfil. Si falla a mitad, el original queda intacto."""
        try:
            escribir_atomico(CONFIG["PERFIL_PATH"], contenido_dict=perfil)
            logger.info("Perfil de usuario actualizado.")
        except IOError as e:
            logger.error(f"Error guardando perfil: {e}")

    def actualizar_perfil_desde_sesion(self, resumen: str) -> None:
        """
        Pide al modelo que extraiga datos del usuario del resumen de sesión
        y los fusiona con el perfil existente.

        AUSENTE EN v6.1 — El perfil de Gemini solo incrementa total_sesiones.
        Restaurado en v6.2 para que el perfil crezca automáticamente.
        """
        perfil = self.cargar_perfil()
        prompt = f"""
Analiza este resumen de conversación. Extrae datos sobre el usuario.
Devuelve ÚNICAMENTE JSON válido, sin texto extra, sin bloques de código markdown.
Si no puedes determinar un campo, usa null.

PERFIL ACTUAL: {json.dumps(perfil, ensure_ascii=False)}
RESUMEN: {resumen}

Formato de respuesta:
{{
  "nivel_python": "nulo/básico/intermedio/avanzado o null",
  "proyectos_activos": ["lista"] o null,
  "temas_frecuentes": ["lista"] o null,
  "preferencias_comunicacion": "descripción o null"
}}
"""
        try:
            raw = self._llamar_ollama(prompt)
            clean = re.sub(r'```(?:json)?|```', '', raw).strip()
            datos = json.loads(clean)
            for k, v in datos.items():
                if v is None:
                    continue
                if k in ("proyectos_activos", "temas_frecuentes") and isinstance(v, list):
                    existentes = perfil.get(k, [])
                    perfil[k] = list(set(existentes + v))[:20]
                else:
                    perfil[k] = v
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"No se pudo parsear JSON del perfil: {e}")

        perfil["ultima_sesion"]  = str(datetime.datetime.now())
        perfil["total_sesiones"] = perfil.get("total_sesiones", 0) + 1
        self.guardar_perfil(perfil)

    def actualizar_perfil_manual(self, campo: str, valor) -> str:
        """Permite al usuario corregir su perfil manualmente desde el CLI."""
        campos_ok = ["nombre", "hardware", "nivel_python", "nivel_otros",
                     "preferencias_comunicacion", "notas_personales"]
        if campo not in campos_ok:
            return f"Campo no permitido. Usa uno de: {campos_ok}"
        perfil = self.cargar_perfil()
        perfil[campo] = valor
        self.guardar_perfil(perfil)
        return f"✅ Perfil actualizado: {campo} = {valor}"

    # ──────────────────────────────────────────────────────────────────────────
    #  SISTEMA DE MEMORIAS
    # ──────────────────────────────────────────────────────────────────────────

    def guardar_memoria(self, id_chat: str, contenido: str, tags: list = []) -> str:
        """
        Guarda memoria con escritura atómica y validación completa.

        DIFERENCIA v6.1 vs v6.2:
        - v6.1: escritura directa (riesgo de corrupción en Windows si se interrumpe)
        - v6.2: escritura atómica vía .tmp + os.replace() (segura en Windows y Linux)
        """
        id_chat = self._validar_id(id_chat)

        if not isinstance(contenido, str) or not contenido.strip():
            raise ValueError("Contenido vacío.")
        if len(contenido.encode("utf-8")) > CONFIG["MAX_CONTENT_BYTES"]:
            raise ValueError(f"Contenido demasiado grande (máx. {CONFIG['MAX_CONTENT_BYTES']//1000}KB).")

        tags_limpios = [str(t).lower().strip()[:50] for t in tags[:20] if str(t).strip()]

        path_md   = os.path.join(self.db_path, f"{id_chat}.md")
        path_json = os.path.join(self.db_path, f"{id_chat}.json")

        # Escritura atómica del contenido (compatible Windows)
        escribir_atomico(path_md, contenido_str=contenido)

        meta = {
            "id":       id_chat,
            "timestamp": str(datetime.datetime.now()),
            "tags":     tags_limpios,
            # v6.1 mejoró esto a 1000 chars: mejor cobertura para BM25. Lo mantenemos.
            "resumen":  contenido[:CONFIG["SNIPPET_LENGTH"]],
            "checksum": hashlib.md5(contenido.encode()).hexdigest(),
            "version":  "6.2",
            "bytes":    len(contenido.encode("utf-8"))
        }
        escribir_atomico(path_json, contenido_dict=meta)

        logger.info(f"Memoria [{id_chat}] guardada. Tags: {tags_limpios}")
        return f"✅ Memoria [{id_chat}] guardada."

    def _cargar_metadatos(self) -> list:
        """
        Carga todos los JSON de la DB con manejo individual de errores.

        AUSENTE EN v6.1: un solo JSON corrupto tumbaba todo recuperar_recuerdos().
        En v6.2 cada archivo se procesa de forma independiente.
        """
        metas = []
        try:
            archivos = os.listdir(self.db_path)
        except OSError as e:
            logger.error(f"No se puede leer db_path: {e}")
            return []

        for archivo in archivos:
            if not archivo.endswith(".json"):
                continue
            path = os.path.join(self.db_path, archivo)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    metas.append(json.load(f))
            except json.JSONDecodeError:
                logger.warning(f"JSON corrupto ignorado: {archivo} — usa :reparar para limpiar")
            except Exception as e:
                logger.error(f"Error leyendo {archivo}: {e}")
        return metas

    # ──────────────────────────────────────────────────────────────────────────
    #  RECUPERACIÓN BM25 CON STEMMING
    # ──────────────────────────────────────────────────────────────────────────

    def _tokenizar(self, texto: str) -> list:
        """
        Tokeniza con stemming en español si nltk está disponible.

        DIFERENCIA CLAVE v6.1 vs v6.2:
        - v6.1: texto.lower().split()  → "proyectos" ≠ "proyecto" (no cruza formas)
        - v6.2: SnowballStemmer        → "proyectos" = "proyecto" = "proyectando"

        El stemming es lo que hace que buscar "memorias" encuentre algo
        indexado con el tag "memoria".
        """
        tokens = re.findall(r'\b[a-záéíóúüñ]{3,}\b', texto.lower())
        if STEMMER:
            return [STEMMER.stem(t) for t in tokens]
        return tokens

    def recuperar_recuerdos(self, query: str, top_k: int = 3) -> str:
        """
        Recupera las memorias más relevantes y las devuelve como bloque de texto.

        FIXES respecto a v6.1:
        1. Stemming en español (v6.1 usaba split simple)
        2. Fix scores negativos con corpus pequeño (bug matemático de BM25Okapi)
        3. Manejo de JSONs corruptos (v6.1 fallaba con cualquier JSON malo)
        4. Límite de contexto explícito (v6.1 podía generar prompts infinitos)

        Devuelve string vacío si no hay memorias relevantes.
        """
        metas = self._cargar_metadatos()
        if not metas:
            return ""

        if not BM25_OK:
            return self._recuperar_keyword_basico(query, metas, top_k)

        # Corpus: tags + resumen de cada memoria (más señal semántica que solo tags)
        corpus_textos = [f"{' '.join(m.get('tags', []))} {m.get('resumen', '')}" for m in metas]
        corpus_tokens = [self._tokenizar(doc) for doc in corpus_textos]
        ids_corpus    = [m["id"] for m in metas]

        if not any(corpus_tokens):
            return ""

        bm25   = BM25Okapi(corpus_tokens)
        q_tok  = self._tokenizar(query)
        if not q_tok:
            return ""

        scores = bm25.get_scores(q_tok)

        # FIX CRÍTICO: BM25Okapi da scores negativos con corpus de 1 documento.
        # Esto es matemáticamente correcto (IDF negativo) pero rompe el filtro "> 0".
        # Solución: ranking relativo. Tomamos el top_k por puntuación descendente
        # y descartamos solo los que están muy por debajo del mejor (umbral relativo).
        pares = sorted(zip(ids_corpus, scores), key=lambda x: x[1], reverse=True)
        if not pares:
            return ""

        max_score = pares[0][1]
        # Un documento es "relevante" si su score está dentro del 60% del mejor.
        # Ejemplo: mejor=0.8 → umbral=0.32. Mejor=-0.5 → umbral=-0.8 (acepta cercanos)
        umbral = max_score - abs(max_score) * 0.4

        seleccionados = [(id_, sc) for id_, sc in pares[:top_k] if sc >= umbral]

        if not seleccionados:
            return ""

        # Construir bloque de contexto con límite explícito
        bloque = ""
        for id_mem, score in seleccionados:
            path = os.path.join(self.db_path, f"{id_mem}.md")
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    contenido = f.read()
                fragmento = f"\n--- MEMORIA: {id_mem} (relevancia: {score:.3f}) ---\n{contenido}\n"

                # FIX: Verificar límite antes de añadir (v6.1 no tenía límite)
                if len(bloque) + len(fragmento) > CONFIG["MAX_CONTEXT_CHARS"]:
                    logger.warning("Límite de contexto alcanzado en recuperación.")
                    bloque += "\n[⚠️ Memorias adicionales omitidas por límite de tokens]\n"
                    break
                bloque += fragmento
            except IOError as e:
                logger.error(f"Error leyendo memoria [{id_mem}]: {e}")

        logger.info(f"BM25 recuperó {len(seleccionados)} memorias para: '{query[:50]}'")
        return bloque

    def _recuperar_keyword_basico(self, query: str, metas: list, top_k: int) -> str:
        """Fallback si rank_bm25 no está instalado. Menos preciso pero funcional."""
        query_words = set(query.lower().split())
        puntuados = []
        for m in metas:
            tags = set(m.get("tags", []))
            score = len(tags.intersection(query_words))
            if score > 0:
                puntuados.append((m["id"], score))
        puntuados.sort(key=lambda x: x[1], reverse=True)

        bloque = ""
        for id_mem, _ in puntuados[:top_k]:
            path = os.path.join(self.db_path, f"{id_mem}.md")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    bloque += f"\n--- MEMORIA: {id_mem} ---\n{f.read()}\n"
        return bloque

    # ──────────────────────────────────────────────────────────────────────────
    #  RESUMEN AUTOMÁTICO DE SESIÓN
    # ──────────────────────────────────────────────────────────────────────────

    def generar_resumen_sesion(self) -> str:
        """
        Pide al modelo que resuma la sesión de forma estructurada.

        DIFERENCIA v6.1 vs v6.2:
        - v6.1: guarda el chat completo en crudo (escala mal, mucho ruido para BM25)
        - v6.2: el modelo genera un resumen denso con campos estructurados
                que luego se indexa con BM25 de forma mucho más eficiente

        Después de 50 sesiones, la diferencia de calidad en recuperación es enorme.
        """
        if not self.historial_sesion:
            return "Sesión sin contenido."

        historial_texto = ""
        for t in self.historial_sesion:
            # Limitamos por turno para no saturar el contexto de resumen
            historial_texto += f"Alex: {t['user'][:400]}\nNexo: {t['nexo'][:600]}\n---\n"

        prompt = f"""
Eres un asistente de análisis. Resume esta conversación de forma estructurada.
Devuelve solo el texto del resumen, sin comentarios adicionales.

CONVERSACIÓN:
{historial_texto}

Formato requerido:
TEMAS: [temas principales separados por coma]
DECISIONES: [decisiones técnicas o conceptuales tomadas]
PENDIENTE: [preguntas o tareas sin resolver]
USUARIO_INFO: [datos detectados del usuario: hardware, nivel, proyectos]
SINOPSIS: [2-3 frases con lo más importante]
"""
        return self._llamar_ollama(prompt)

    def cerrar_sesion(self) -> str:
        """
        Cierra la sesión:
          1. Genera resumen estructurado (no el chat en crudo como v6.1)
          2. Guarda como memoria indexada
          3. Actualiza el perfil del usuario
          4. Limpia el historial en memoria

        DIFERENCIA con v6.1:
        - v6.1 guardaba el chat completo con tags genéricos ["historial", "aprendizaje"]
          → BM25 recupera toda la sesión siempre, con mucho ruido
        - v6.2 guarda el resumen denso con tags extraídos del contenido real
          → BM25 recupera solo lo que es relevante para la pregunta actual
        """
        if not self.historial_sesion:
            return "Sesión vacía, nada que guardar."

        print("\n⏳ Generando resumen de sesión...")
        resumen = self.generar_resumen_sesion()

        # Extraer tags de la línea TEMAS del resumen
        tags = ["historial"]
        for linea in resumen.split("\n"):
            if linea.startswith("TEMAS:"):
                raw_tags = linea.replace("TEMAS:", "").strip()
                tags += [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
                break
        tags.append(self.sesion_inicio.strftime("sesion_%Y%m"))

        try:
            self.guardar_memoria(self.sesion_id, resumen, tags)
        except Exception as e:
            logger.error(f"Error guardando resumen de sesión: {e}")

        self.actualizar_perfil_desde_sesion(resumen)
        self.historial_sesion = []

        return f"✅ Sesión [{self.sesion_id}] guardada.\n\nResumen:\n{resumen}"

    # ──────────────────────────────────────────────────────────────────────────
    #  CONTEXTO DE ARRANQUE (BOOT CONTEXT)
    # ──────────────────────────────────────────────────────────────────────────

    def construir_boot_context(self, pregunta: str = "") -> str:
        """
        Construye el bloque que se inyecta al inicio de CADA prompt.

        AUSENTE EN v6.1 — Esta es la feature más importante para la experiencia
        de usuario. Sin boot context, cada consulta es independiente y la IA
        no sabe quién eres ni qué estás haciendo.

        Con boot context, la IA sabe desde el primer mensaje:
        - Quién eres y tu nivel técnico
        - En qué proyecto estás
        - Qué decidiste en sesiones anteriores (via memorias BM25)
        - Cuál es tu hardware (para calibrar respuestas)
        """
        hw      = self._get_hw()
        perfil  = self.cargar_perfil()
        proyect = ", ".join(perfil.get("proyectos_activos", [])) or "ninguno registrado"
        temas   = ", ".join(perfil.get("temas_frecuentes", [])[:8]) or "sin historial"
        modo    = "⚠️ MODO CONCISO: CPU alta, sé muy breve." if self._cpu_alta() else ""

        # Memorias relevantes para la pregunta actual
        memorias_ctx = ""
        if pregunta:
            memorias_ctx = self.recuperar_recuerdos(pregunta, top_k=3)

        return f"""
SISTEMA: {hw} | Plataforma: {'Windows' if IS_WINDOWS else 'Linux/Mac'} {modo}

=== PERFIL DEL USUARIO ===
Nombre        : {perfil.get('nombre', 'Alex')}
Hardware      : {perfil.get('hardware', 'Acer Nitro')}
Nivel Python  : {perfil.get('nivel_python', 'intermedio')}
Otros         : {json.dumps(perfil.get('nivel_otros', {}), ensure_ascii=False)}
Proyectos     : {proyect}
Temas frecuentes: {temas}
Sesiones      : {perfil.get('total_sesiones', 0)}
Última sesión : {perfil.get('ultima_sesion', 'primera vez')}
Preferencias  : {perfil.get('preferencias_comunicacion', 'directo y técnico')}

{memorias_ctx}

=== INSTRUCCIONES ===
Eres 'Nexo', el asistente de IA local de {perfil.get('nombre', 'Alex')}.
Tienes DOS capacidades que combinas de forma natural:
  1. MEMORIA PERSONAL: acceso al historial y diarios de Alex. Usala cuando sea relevante.
  2. CONOCIMIENTO GENERAL: todo tu conocimiento como Llama 3.1. Usalo siempre libremente.
Responde en espanol, con estilo directo y tecnico.
Si la pregunta es sobre Alex o sus proyectos: consulta las memorias primero.
Si la pregunta es general (codigo, ciencia, historia, matematicas, cualquier tema): responde directamente.
Nunca digas que no puedes responder algo por falta de memorias. Las memorias son contexto extra, no un limite.
""".strip()

    # ──────────────────────────────────────────────────────────────────────────
    #  PROMPT CONDICIONAL (FIX v6.1)
    # ──────────────────────────────────────────────────────────────────────────

    def _construir_prompt_principal(self, pregunta: str, boot: str) -> str:
        """
        FIX CLAVE respecto a v6.1:

        v6.1 tenía un prompt fijo que decía "TIENES ACCESO a memorias pasadas.
        Si la información está abajo, ÚSALA." pero si el contexto estaba vacío,
        el modelo recibía esa instrucción sin datos y podía alucinar inventando
        recuerdos ("sí recuerdo que hablamos de X" cuando nunca lo hicimos).

        v6.2 tiene un prompt CONDICIONAL:
        - Si hay contexto de memorias: instrucción explícita de usarlo
        - Si no hay contexto: instrucción explícita de NO inventar recuerdos
        """
        # Detectar si el boot context incluye memorias recuperadas
        hay_memorias = "--- MEMORIA:" in boot

        if hay_memorias:
            instruccion_memoria = (
                "Tienes memorias personales de Alex en el contexto de arriba. "
                "ÚSALAS cuando sean relevantes para responder con precisión. "
                "Para todo lo demás, usa libremente tu conocimiento general como lo haría "
                "cualquier asistente de IA: explica conceptos, responde preguntas técnicas, "
                "ayuda con código, matemáticas, ciencia, cultura, o cualquier tema. "
                "Eres un asistente completo, no solo un buscador de memorias."
            )
        else:
            instruccion_memoria = (
                "No hay memorias personales de Alex relevantes para esta pregunta. "
                "Responde usando todo tu conocimiento general con total libertad: "
                "puedes explicar cualquier concepto, ayudar con código, resolver problemas, "
                "debatir ideas, o responder sobre cualquier tema como lo haría un asistente "
                "de IA completo. NO inventes recuerdos de conversaciones pasadas, "
                "pero SÍ usa todo tu conocimiento del mundo para dar la mejor respuesta posible."
            )

        # Historial de la sesión actual (últimos 6 turnos para no saturar)
        historial = ""
        if self.historial_sesion:
            historial = "\n=== HISTORIAL DE ESTA SESIÓN ===\n"
            for t in self.historial_sesion[-6:]:
                historial += f"Alex: {t['user']}\nNexo: {t['nexo']}\n"

        return f"""
{boot}

{historial}

=== INSTRUCCIÓN DE MEMORIA ===
{instruccion_memoria}

=== PREGUNTA ===
Alex: {pregunta}
Nexo:""".strip()

    # ──────────────────────────────────────────────────────────────────────────
    #  COMUNICACIÓN CON OLLAMA
    # ──────────────────────────────────────────────────────────────────────────

    def _verificar_ollama(self) -> None:
        """Falla rápido y claro si Ollama no está corriendo."""
        try:
            r = requests.get(CONFIG["OLLAMA_HEALTH"], timeout=3)
            if r.status_code == 200:
                modelos = [m.get("name", "") for m in r.json().get("models", [])]
                logger.info(f"✅ Ollama online. Modelos disponibles: {modelos}")
                if CONFIG["MODELO_PRINCIPAL"] not in modelos and modelos:
                    logger.warning(
                        f"⚠️ '{CONFIG['MODELO_PRINCIPAL']}' no encontrado. "
                        f"Disponibles: {modelos}. "
                        f"Cambia MODELO_PRINCIPAL en CONFIG o ejecuta: ollama pull llama3.1"
                    )
        except requests.exceptions.ConnectionError:
            logger.error("❌ Ollama NO responde. Ejecuta: ollama serve")
        except Exception as e:
            logger.warning(f"Verificación Ollama con error: {e}")

    def _llamar_ollama(self, prompt: str) -> str:
        """Capa centralizada de comunicación con Ollama con manejo completo de errores."""
        payload = {
            "model":  CONFIG["MODELO_PRINCIPAL"],
            "prompt": prompt,
            "stream": False
        }
        try:
            r = requests.post(
                CONFIG["OLLAMA_ENDPOINT"],
                json=payload,
                timeout=CONFIG["TIMEOUT_INFERENCIA"]
            )
            r.raise_for_status()
            return r.json().get("response", "Respuesta vacía del modelo.")
        except requests.exceptions.ConnectionError:
            return "❌ Ollama no responde. ¿Está corriendo? → ollama serve"
        except requests.exceptions.Timeout:
            return (
                f"⏱️ Timeout ({CONFIG['TIMEOUT_INFERENCIA']}s). "
                f"Con RTX 5060 no debería pasar. Verifica que Ollama esté usando la GPU: "
                f"ollama run llama3.1 y observa el uso de VRAM."
            )
        except requests.exceptions.HTTPError as e:
            return f"❌ Error HTTP de Ollama: {e}"
        except Exception as e:
            logger.error(f"Error inesperado en Ollama: {e}", exc_info=True)
            return "❌ Error interno. Revisa nexo_audit.log."


    def _llamar_ollama_vision(self, prompt: str, imagen_b64: str) -> str:
        """
        Llama al modelo de visión (llama3.2-vision) con una imagen en base64.

        SEPARADO de _llamar_ollama intencionalmente:
        - Usa MODELO_VISION en lugar de MODELO_PRINCIPAL
        - Incluye el campo 'images' en el payload (solo lo acepta el modelo vision)
        - Timeout mayor (120s) porque procesar imágenes es más lento que texto
        - Manejo de error específico si el modelo no está instalado

        CUÁNDO LLAMAR A ESTE MÉTODO:
        Solo desde el dashboard cuando el usuario sube una imagen o captura.
        El chat normal (texto) siempre usa _llamar_ollama con MODELO_PRINCIPAL.

        PARÁMETRO imagen_b64:
        String base64 de la imagen. El dashboard lo genera con:
            base64.b64encode(archivo.getvalue()).decode("utf-8")
        """
        payload = {
            "model":  CONFIG["MODELO_VISION"],
            "prompt": prompt,
            "images": [imagen_b64],  # Ollama espera lista de strings base64
            "stream": False
        }
        try:
            r = requests.post(
                CONFIG["OLLAMA_ENDPOINT"],
                json=payload,
                timeout=120  # Imágenes necesitan más tiempo que texto
            )
            r.raise_for_status()
            return r.json().get("response", "Sin respuesta del modelo de visión.")
        except requests.exceptions.ConnectionError:
            return "❌ Ollama no responde. ¿Está corriendo? → ollama serve"
        except requests.exceptions.Timeout:
            return "⏱️ Timeout analizando imagen. Prueba con una imagen más pequeña o resolución menor."
        except requests.exceptions.HTTPError as e:
            # 404 suele significar que el modelo no está instalado en Ollama
            if "404" in str(e):
                return (
                    "❌ llama3.2-vision no está instalado en Ollama. "
                    "Ejecuta: ollama pull llama3.2-vision (pesa ~7GB)"
                )
            return f"❌ Error HTTP de Ollama Vision: {e}"
        except Exception as e:
            logger.error(f"Error inesperado en Ollama Vision: {e}", exc_info=True)
            return "❌ Error interno procesando imagen. Revisa nexo_audit.log."

    # ──────────────────────────────────────────────────────────────────────────
    #  MOTOR DE INFERENCIA PRINCIPAL
    # ──────────────────────────────────────────────────────────────────────────

    def despertar_nexo(self, pregunta: str, cliente: str = "local") -> str:
        """
        Orquesta todos los bloques: validación → boot context → prompt → Ollama → historial.
        """
        # Rate limit
        try:
            self._check_rate_limit(cliente)
        except PermissionError as e:
            return str(e)

        # Validar pregunta
        try:
            pregunta = self._validar_query(pregunta)
        except ValueError as e:
            return f"Error: {e}"

        # Boot context (perfil + memorias BM25 relevantes)
        boot = self.construir_boot_context(pregunta)

        # Prompt completo con lógica condicional de memorias
        prompt = self._construir_prompt_principal(pregunta, boot)

        logger.info(f"[{cliente}] Query: '{pregunta[:60]}'")
        respuesta = self._llamar_ollama(prompt)

        # Añadir al historial de sesión
        self.historial_sesion.append({"user": pregunta, "nexo": respuesta})

        return respuesta

    # ──────────────────────────────────────────────────────────────────────────
    #  UTILIDADES DE MANTENIMIENTO
    # ──────────────────────────────────────────────────────────────────────────

    def reparar_indices(self) -> str:
        """Detecta archivos huérfanos (.md sin .json o viceversa)."""
        try:
            archivos  = os.listdir(self.db_path)
        except OSError as e:
            return f"Error leyendo DB: {e}"
        mds   = {f[:-3] for f in archivos if f.endswith(".md")}
        jsons = {f[:-5] for f in archivos if f.endswith(".json")}
        h_md  = mds   - jsons
        h_js  = jsons - mds
        if not h_md and not h_js:
            return "✅ Base de datos íntegra."
        informe = []
        if h_md:  informe.append(f"⚠️ .md sin .json: {h_md}")
        if h_js:  informe.append(f"⚠️ .json sin .md: {h_js}")
        return "\n".join(informe)

    def listar_memorias(self) -> list:
        """Lista todas las memorias con preview para el CLI."""
        metas = self._cargar_metadatos()
        resultado = [{
            "id":      m.get("id", "?"),
            "ts":      m.get("timestamp", "?")[:16],
            "tags":    m.get("tags", []),
            "preview": m.get("resumen", "")[:80],
            "kb":      round(m.get("bytes", 0) / 1000, 1)
        } for m in metas]
        return sorted(resultado, key=lambda x: x["ts"], reverse=True)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI INTERACTIVA
# ══════════════════════════════════════════════════════════════════════════════

def cli():
    nexo = NexoCompleto()
    perfil = nexo.cargar_perfil()

    print("\n" + "═" * 58)
    print(f"  NEXO v6.2 | Modelo: {CONFIG['MODELO_PRINCIPAL']}")
    print(f"  Windows: {IS_WINDOWS} | BM25: {BM25_OK} | Stemming: {NLTK_OK}")
    print("  :ayuda para ver comandos disponibles")
    print("═" * 58)

    if perfil.get("total_sesiones", 0) > 0:
        print(f"\n👋 Bienvenido de vuelta, {perfil.get('nombre', 'Alex')}.")
        print(f"   Última sesión : {perfil.get('ultima_sesion', '?')}")
        print(f"   Total sesiones: {perfil.get('total_sesiones', 0)}")
    else:
        print(f"\n👋 Primera sesión. Nexo aprenderá contigo.")
    print()

    while True:
        try:
            entrada = input("Tú → ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nCerrando sesión...")
            print(nexo.cerrar_sesion())
            break

        if not entrada:
            continue

        # ── Comandos especiales ──────────────────────────────────────────────

        if entrada == ":ayuda":
            print(textwrap.dedent("""
            ┌─ COMANDOS ─────────────────────────────────────────────┐
            │  :ayuda              — Esta ayuda                      │
            │  :perfil             — Ver perfil actual               │
            │  :perfil set C V     — Actualizar campo C con valor V  │
            │  :memorias           — Listar memorias guardadas       │
            │  :guardar ID         — Guardar nueva memoria           │
            │  :buscar TEXTO       — Buscar memorias relevantes      │
            │  :reparar            — Verificar integridad DB         │
            │  :salir              — Cerrar y guardar sesión         │
            │  :salir-rapido       — Salir sin guardar               │
            └────────────────────────────────────────────────────────┘
            """))

        elif entrada == ":perfil":
            perfil = nexo.cargar_perfil()
            print("\n── PERFIL ──")
            for k, v in perfil.items():
                if k != "version_perfil":
                    print(f"  {k:32}: {v}")
            print()

        elif entrada.startswith(":perfil set "):
            partes = entrada[len(":perfil set "):].split(" ", 1)
            if len(partes) == 2:
                print(nexo.actualizar_perfil_manual(partes[0], partes[1]))
            else:
                print("Uso: :perfil set CAMPO VALOR")

        elif entrada == ":memorias":
            mems = nexo.listar_memorias()
            if not mems:
                print("No hay memorias guardadas.")
            else:
                print(f"\n── {len(mems)} MEMORIAS ──")
                for m in mems:
                    print(f"  [{m['id']}] {m['ts']} | {m['kb']}KB | {m['tags']}")
                    print(f"    {m['preview']}...")
            print()

        elif entrada.startswith(":guardar "):
            id_nuevo = entrada[len(":guardar "):].strip()
            print(f"Contenido para [{id_nuevo}] (línea vacía para terminar):")
            lineas = []
            while True:
                l = input("  > ")
                if l == "": break
                lineas.append(l)
            if lineas:
                tags_raw = input("Tags (coma): ")
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                try:
                    print(nexo.guardar_memoria(id_nuevo, "\n".join(lineas), tags))
                except ValueError as e:
                    print(f"Error: {e}")

        elif entrada.startswith(":buscar "):
            q = entrada[len(":buscar "):].strip()
            resultado = nexo.recuperar_recuerdos(q)
            print(resultado if resultado else "Sin memorias relevantes.")

        elif entrada == ":reparar":
            print(nexo.reparar_indices())

        elif entrada == ":salir":
            print(nexo.cerrar_sesion())
            print("\n👋 ¡Hasta la próxima!")
            break

        elif entrada == ":salir-rapido":
            print("👋 Saliendo sin guardar.")
            break

        else:
            print("Nexo → ", end="", flush=True)
            print(nexo.despertar_nexo(entrada))
            print()


# ══════════════════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexo de Consciencia v6.2")
    parser.add_argument("--setup", action="store_true",
                        help="Descarga recursos de NLTK (ejecutar solo la primera vez)")
    args = parser.parse_args()

    if args.setup:
        try:
            import nltk
            print("Descargando recursos NLTK para español...")
            nltk.download("punkt",     quiet=True)
            nltk.download("stopwords", quiet=True)
            print("✅ Setup completado. Ejecuta: python nexo_consciencia_v6_2.py")
        except ImportError:
            print("❌ nltk no instalado: pip install nltk")
    else:
        cli()
