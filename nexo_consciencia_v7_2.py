"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        NEXO DE CONSCIENCIA v7.2 — ELITE EDITION                            ║
║        Autor original  : AlexMedran-exe                                    ║
║        Arquitectura    : Claude (Anthropic)                                ║
║        Colaboración    : Gemini (Google)                                   ║
║                                                                              ║
║  NOVEDADES v7.2:                                                            ║
║    ✅ System prompt rediseñado: identidad de Orquestador de Élite           ║
║    ✅ Sección [SEGUNDA OPINIÓN] en respuestas complejas                     ║
║    ✅ Soporte de audio: transcripción con Whisper (modelo base)             ║
║    ✅ Re-indexación BM25 inmediata tras cada guardado                       ║
║    ✅ Schema JSON ampliado: token_count, model_used, session_id             ║
║    ✅ Thread-safe: bloqueo de escritura con threading.Lock                  ║
║    ✅ encoding=utf-8 obligatorio en todas las operaciones de archivo        ║
║    ✅ Todas las protecciones de seguridad de v6.2 intactas                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

INSTALACIÓN:
    py -3.11 -m pip install psutil requests rank_bm25 nltk openai-whisper

PRIMERA EJECUCIÓN:
    py -3.11 nexo_consciencia_v7_2.py --setup

NOTA SOBRE WHISPER:
    Whisper descarga el modelo 'base' (~150MB) en el primer uso.
    Se guarda en cache y no vuelve a descargarse.
    Usar 'base' y NO 'medium'/'large' para no saturar VRAM junto a Llama 3.1.
"""

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
import threading

IS_WINDOWS = sys.platform == "win32"
if not IS_WINDOWS:
    import fcntl

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
    print("Aviso: rank_bm25 no instalado. Instalar: pip install rank_bm25")

try:
    from nltk.stem.snowball import SnowballStemmer
    STEMMER = SnowballStemmer("spanish")
    NLTK_OK = True
except ImportError:
    STEMMER = None
    NLTK_OK = False

try:
    import whisper as _whisper_lib
    WHISPER_OK = True
except ImportError:
    WHISPER_OK = False

if _missing:
    sys.exit(f"Librerias faltantes: {_missing}. Ejecuta: pip install {' '.join(_missing)}")


CONFIG = {
    "DB_PATH":            "db_consciencias",
    "PERFIL_PATH":        "perfil_usuario.json",
    "AUDIT_LOG":          "nexo_audit.log",
    "OLLAMA_ENDPOINT":    "http://localhost:11434/api/generate",
    "OLLAMA_HEALTH":      "http://localhost:11434/api/tags",
    "MODELO_PRINCIPAL":   "llama3.1:latest",
    "MODELO_VISION":      "llama3.2-vision:latest",
    "MODELO_WHISPER":     "base",
    "TIMEOUT_INFERENCIA": 120,
    "MAX_ID_LENGTH":      64,
    "MAX_QUERY_LENGTH":   2000,
    "MAX_CONTENT_BYTES":  200_000,
    "MAX_CONTEXT_CHARS":  12_000,
    "MAX_IDS_FUSION":     10,
    "RATE_LIMIT_SEG":     3,
    "SNIPPET_LENGTH":     1000,
    "HW_CACHE_SEG":       15,
    "CPU_UMBRAL_ALTO":    80,
    "ID_PATTERN":         re.compile(r'^[a-zA-Z0-9_\-]{1,64}$'),
}

# System prompt rediseñado: identidad fuerte sin artificios que confunden al modelo
# El truco real no es "PROHIBIR disculpas" (eso raramente funciona con LLMs locales)
# sino dar una identidad clara, instrucciones concretas y ejemplos de formato esperado.
SYSTEM_PROMPT = """Eres EL NEXO, el motor de razonamiento local de {nombre}.
Hardware: {hardware}. Plataforma: {plataforma}.

IDENTIDAD:
Eres un orquestador de conocimiento de élite. Tienes acceso a:
  1. Tu entrenamiento completo como Llama 3.1 (conocimiento general hasta tu fecha de corte)
  2. Memorias personales de {nombre} inyectadas como contexto (PRIORIDAD ABSOLUTA)

REGLAS DE COMPORTAMIENTO:
- Responde con autoridad y precisión. Sin rodeos ni cortesía excesiva.
- Si la pregunta es técnica: baja al detalle. Variables, comparativas, materiales, código.
- Si hay conflicto entre tu entrenamiento y una memoria: LA MEMORIA MANDA.
- Usa Markdown: tablas para comparativas, bloques de código, negritas para conceptos clave.
- Responde siempre en el idioma del usuario.

SECCIÓN OBLIGATORIA EN RESPUESTAS COMPLEJAS:
Cuando la respuesta tenga más de 3 párrafos o sea una decisión técnica importante,
añade al final una sección:

[SEGUNDA OPINIÓN]
Un punto de vista crítico o mejora que el usuario probablemente no ha considerado.
Máximo 2-3 frases. Directo. Sin introducción.

PERFIL DEL USUARIO:
{perfil_texto}

{memorias_ctx}
""".strip()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["AUDIT_LOG"], encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NexoV7_2")


def escribir_atomico(path: str, contenido_str: str = None, contenido_dict: dict = None):
    """
    Escritura atómica multiplataforma con encoding UTF-8 obligatorio.
    Resuelve: corrupción de archivos, caracteres especiales españoles,
    interrupciones de proceso a mitad de escritura.
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
        os.replace(path_tmp, path)
    except Exception as e:
        if os.path.exists(path_tmp):
            try:
                os.remove(path_tmp)
            except OSError:
                pass
        raise IOError(f"Escritura atomica fallida en {path}: {e}")


class NexoCompleto:
    """
    Motor central de Nexo de Consciencia v7.2.
    Thread-safe mediante threading.Lock para escrituras concurrentes.
    Re-indexacion BM25 inmediata tras cada guardado.
    """

    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), CONFIG["DB_PATH"])
        os.makedirs(self.db_path, exist_ok=True)

        self._hw_cache = ""
        self._hw_ts    = 0
        self._rl       = {}
        self._lock     = threading.Lock()  # Thread-safe para escrituras

        # Cache BM25 en memoria: se actualiza tras cada guardar_memoria()
        # Evita reconstruir el indice desde disco en cada consulta
        self._bm25_cache        = None
        self._bm25_ids          = []
        self._bm25_textos       = []
        self._bm25_ultima_build = 0

        self.historial_sesion = []
        self.sesion_id        = datetime.datetime.now().strftime("sesion_%Y%m%d_%H%M%S")
        self.sesion_inicio    = datetime.datetime.now()

        # Modelo Whisper (carga lazy: solo cuando se necesita)
        self._whisper_model = None

        logger.info(f"NexoCompleto v7.2 | Windows={IS_WINDOWS} | Sesion: {self.sesion_id}")
        self._verificar_ollama()

    # ── SEGURIDAD ─────────────────────────────────────────────────────────────

    def _validar_id(self, id_chat: str) -> str:
        if not isinstance(id_chat, str):
            raise ValueError("El ID debe ser texto.")
        if not CONFIG["ID_PATTERN"].match(id_chat):
            raise ValueError(
                f"ID invalido: '{id_chat}'. Solo letras, numeros, _ y -. "
                f"Maximo {CONFIG['MAX_ID_LENGTH']} caracteres."
            )
        ruta_obj  = os.path.realpath(os.path.join(self.db_path, id_chat))
        ruta_base = os.path.realpath(self.db_path)
        if not ruta_obj.startswith(ruta_base + os.sep):
            raise PermissionError(f"Intento de acceso fuera de db_path: {id_chat}")
        return id_chat

    def _validar_query(self, q: str) -> str:
        if not isinstance(q, str) or not q.strip():
            raise ValueError("La consulta no puede estar vacia.")
        if len(q) > CONFIG["MAX_QUERY_LENGTH"]:
            raise ValueError(f"Consulta demasiado larga (max. {CONFIG['MAX_QUERY_LENGTH']} chars).")
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', q).strip()

    def _check_rate_limit(self, cliente: str = "local"):
        ahora  = time.time()
        ultima = self._rl.get(cliente, 0)
        espera = ahora - ultima
        if espera < CONFIG["RATE_LIMIT_SEG"]:
            raise PermissionError(f"Rate limit: espera {CONFIG['RATE_LIMIT_SEG'] - espera:.1f}s.")
        self._rl[cliente] = ahora

    # ── HARDWARE ──────────────────────────────────────────────────────────────

    def _get_hw(self) -> str:
        ahora = time.time()
        if ahora - self._hw_ts > CONFIG["HW_CACHE_SEG"]:
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                ram = psutil.virtual_memory()
                bat = psutil.sensors_battery()
                bat_str = f"{bat.percent:.0f}%" if bat else "AC"
                self._hw_cache = (
                    f"CPU:{cpu:.0f}% RAM:{ram.percent:.0f}% "
                    f"({ram.used/1e9:.1f}/{ram.total/1e9:.1f}GB) BAT:{bat_str}"
                )
            except Exception as e:
                self._hw_cache = "HW:N/A"
                logger.warning(f"Error telemetria: {e}")
            self._hw_ts = ahora
        return self._hw_cache

    def _cpu_alta(self) -> bool:
        try:
            return psutil.cpu_percent(interval=0.1) > CONFIG["CPU_UMBRAL_ALTO"]
        except Exception:
            return False

    def get_hw_detalle(self) -> dict:
        """Devuelve telemetria detallada para el dashboard."""
        try:
            cpu     = psutil.cpu_percent(interval=0.1)
            ram     = psutil.virtual_memory()
            bat     = psutil.sensors_battery()
            disco   = psutil.disk_usage(os.getcwd())
            return {
                "cpu_pct":    cpu,
                "ram_pct":    ram.percent,
                "ram_used_gb": round(ram.used / 1e9, 1),
                "ram_total_gb": round(ram.total / 1e9, 1),
                "disco_libre_gb": round(disco.free / 1e9, 1),
                "bat_pct":    bat.percent if bat else None,
                "bat_cargando": bat.power_plugged if bat else None,
            }
        except Exception:
            return {}

    # ── PERFIL ────────────────────────────────────────────────────────────────

    def cargar_perfil(self) -> dict:
        perfil_base = {
            "nombre":                    "Alex",
            "hardware":                  "Acer Nitro (RTX 5060, 32GB RAM DDR5, Windows 11 Pro)",
            "nivel_python":              "intermedio (aprendiendo)",
            "nivel_otros":               {"Java": "basico"},
            "proyectos_activos":         ["nexo_consciencia"],
            "temas_frecuentes":          [],
            "preferencias_comunicacion": "respuestas directas y tecnicas",
            "notas_personales":          "",
            "total_sesiones":            0,
            "ultima_sesion":             None,
            "version_perfil":            "7.2"
        }
        path = CONFIG["PERFIL_PATH"]
        if not os.path.exists(path):
            return perfil_base
        try:
            with open(path, "r", encoding="utf-8") as f:
                datos = json.load(f)
            perfil_base.update(datos)
            return perfil_base
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error cargando perfil: {e}. Usando defaults.")
            return perfil_base

    def guardar_perfil(self, perfil: dict) -> None:
        try:
            escribir_atomico(CONFIG["PERFIL_PATH"], contenido_dict=perfil)
            logger.info("Perfil de usuario actualizado.")
        except IOError as e:
            logger.error(f"Error guardando perfil: {e}")

    def actualizar_perfil_desde_sesion(self, resumen: str) -> None:
        perfil = self.cargar_perfil()
        prompt = f"""
Analiza este resumen de conversacion. Extrae datos sobre el usuario.
Devuelve UNICAMENTE JSON valido, sin texto extra, sin bloques de codigo.
Si no puedes determinar un campo, usa null.

PERFIL ACTUAL: {json.dumps(perfil, ensure_ascii=False)}
RESUMEN: {resumen}

Formato:
{{
  "nivel_python": null,
  "proyectos_activos": null,
  "temas_frecuentes": null,
  "preferencias_comunicacion": null
}}
"""
        try:
            raw   = self._llamar_ollama(prompt)
            clean = re.sub(r'```(?:json)?|```', '', raw).strip()
            datos = json.loads(clean)
            for k, v in datos.items():
                if v is None:
                    continue
                if k in ("proyectos_activos", "temas_frecuentes") and isinstance(v, list):
                    existentes = perfil.get(k, [])
                    perfil[k]  = list(set(existentes + v))[:20]
                else:
                    perfil[k] = v
        except Exception as e:
            logger.warning(f"No se pudo actualizar perfil automaticamente: {e}")

        perfil["ultima_sesion"]  = str(datetime.datetime.now())
        perfil["total_sesiones"] = perfil.get("total_sesiones", 0) + 1
        self.guardar_perfil(perfil)

    def actualizar_perfil_manual(self, campo: str, valor) -> str:
        campos_ok = ["nombre", "hardware", "nivel_python", "nivel_otros",
                     "preferencias_comunicacion", "notas_personales"]
        if campo not in campos_ok:
            return f"Campo no permitido. Usa uno de: {campos_ok}"
        perfil = self.cargar_perfil()
        perfil[campo] = valor
        self.guardar_perfil(perfil)
        return f"Perfil actualizado: {campo} = {valor}"

    # ── SISTEMA DE MEMORIAS (thread-safe + re-indexacion inmediata) ────────────

    def guardar_memoria(self, id_chat: str, contenido: str, tags: list = []) -> tuple:
        """
        Guarda memoria con:
        - Validacion completa de entrada
        - Escritura atomica UTF-8
        - Schema JSON ampliado (session_id, model_used, token_count)
        - Thread-safe con threading.Lock
        - Re-indexacion BM25 inmediata
        - Devuelve (mensaje_str, exito_bool) para que el dashboard pueda
          mostrar st.success o st.error segun corresponda
        """
        try:
            id_chat = self._validar_id(id_chat)

            if not isinstance(contenido, str) or not contenido.strip():
                return "Contenido vacio.", False

            # Limpiar contenido de caracteres no serializables
            contenido_limpio = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', contenido)

            tam = len(contenido_limpio.encode("utf-8"))
            if tam > CONFIG["MAX_CONTENT_BYTES"]:
                return f"Contenido demasiado grande ({tam//1000}KB, max {CONFIG['MAX_CONTENT_BYTES']//1000}KB).", False

            tags_limpios = [str(t).lower().strip()[:50] for t in tags[:20] if str(t).strip()]

            path_md   = os.path.join(self.db_path, f"{id_chat}.md")
            path_json = os.path.join(self.db_path, f"{id_chat}.json")

            # Schema JSON ampliado (peticion de Gemini)
            meta = {
                "id":          id_chat,
                "session_id":  self.sesion_id,
                "timestamp":   str(datetime.datetime.now()),
                "tags":        tags_limpios,
                "resumen":     contenido_limpio[:CONFIG["SNIPPET_LENGTH"]],
                "checksum":    hashlib.md5(contenido_limpio.encode("utf-8")).hexdigest(),
                "version":     "7.2",
                "bytes":       tam,
                "token_count": len(contenido_limpio.split()),  # Aproximacion rapida
                "model_used":  CONFIG["MODELO_PRINCIPAL"],
                "md_ref":      f"{id_chat}.md",
            }

            # Escritura thread-safe
            with self._lock:
                escribir_atomico(path_md,   contenido_str=contenido_limpio)
                escribir_atomico(path_json, contenido_dict=meta)

            # Re-indexacion BM25 inmediata: invalida el cache para forzar rebuild
            self._bm25_cache = None
            self._bm25_ultima_build = 0

            logger.info(f"Memoria [{id_chat}] guardada. {tam}B. Tags: {tags_limpios}")
            return f"Memoria [{id_chat}] guardada.", True

        except PermissionError as e:
            logger.error(f"Acceso denegado guardando [{id_chat}]: {e}")
            return f"Error de seguridad: {e}", False
        except IOError as e:
            logger.error(f"Error de escritura [{id_chat}]: {e}")
            return f"Error de escritura: {e}. Revisa nexo_audit.log.", False
        except Exception as e:
            logger.error(f"Error inesperado guardando [{id_chat}]: {e}", exc_info=True)
            return f"Error interno: {e}. Revisa nexo_audit.log.", False

    def _cargar_metadatos(self) -> list:
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
                logger.warning(f"JSON corrupto ignorado: {archivo}")
            except Exception as e:
                logger.error(f"Error leyendo {archivo}: {e}")
        return metas

    # ── BM25 CON CACHE Y RE-INDEXACION INMEDIATA ──────────────────────────────

    def _tokenizar(self, texto: str) -> list:
        tokens = re.findall(r'\b[a-zA-Zaeiouaeiouun]{3,}\b', texto.lower())
        if STEMMER:
            return [STEMMER.stem(t) for t in tokens]
        return tokens

    def _construir_indice_bm25(self) -> None:
        """Construye el indice BM25 en memoria desde los metadatos en disco."""
        metas = self._cargar_metadatos()
        if not metas:
            self._bm25_cache  = None
            self._bm25_ids    = []
            return
        corpus_textos  = [f"{' '.join(m.get('tags', []))} {m.get('resumen', '')}" for m in metas]
        corpus_tokens  = [self._tokenizar(doc) for doc in corpus_textos]
        self._bm25_ids = [m["id"] for m in metas]
        if any(corpus_tokens):
            self._bm25_cache = BM25Okapi(corpus_tokens)
        else:
            self._bm25_cache = None
        self._bm25_ultima_build = time.time()
        logger.info(f"Indice BM25 construido: {len(metas)} documentos.")

    def recuperar_recuerdos(self, query: str, top_k: int = 3) -> str:
        if not BM25_OK:
            return self._recuperar_keyword_basico(query, self._cargar_metadatos(), top_k)

        # Reconstruir indice si esta invalidado (por nuevo guardado) o es la primera vez
        if self._bm25_cache is None:
            self._construir_indice_bm25()

        if self._bm25_cache is None or not self._bm25_ids:
            return ""

        q_tok = self._tokenizar(query)
        if not q_tok:
            return ""

        scores = self._bm25_cache.get_scores(q_tok)
        pares  = sorted(zip(self._bm25_ids, scores), key=lambda x: x[1], reverse=True)
        if not pares:
            return ""

        max_score = pares[0][1]
        umbral    = max_score - abs(max_score) * 0.4
        seleccionados = [(id_, sc) for id_, sc in pares[:top_k] if sc >= umbral]

        if not seleccionados:
            return ""

        bloque = ""
        for id_mem, score in seleccionados:
            path = os.path.join(self.db_path, f"{id_mem}.md")
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    contenido = f.read()
                fragmento = f"\n--- MEMORIA: {id_mem} (relevancia: {score:.3f}) ---\n{contenido}\n"
                if len(bloque) + len(fragmento) > CONFIG["MAX_CONTEXT_CHARS"]:
                    bloque += "\n[Memorias adicionales omitidas por limite de contexto]\n"
                    break
                bloque += fragmento
            except IOError as e:
                logger.error(f"Error leyendo memoria [{id_mem}]: {e}")

        logger.info(f"BM25 recupero {len(seleccionados)} memorias para: '{query[:50]}'")
        return bloque

    def _recuperar_keyword_basico(self, query: str, metas: list, top_k: int) -> str:
        query_words = set(query.lower().split())
        puntuados   = []
        for m in metas:
            tags  = set(m.get("tags", []))
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

    # ── SISTEMA DE VOZ (WHISPER) ───────────────────────────────────────────────

    def cargar_whisper(self) -> bool:
        """
        Carga el modelo Whisper de forma lazy (solo cuando se necesita).
        Usa modelo 'base' para no saturar VRAM junto a Llama 3.1.
        Devuelve True si la carga fue exitosa.
        """
        if not WHISPER_OK:
            return False
        if self._whisper_model is not None:
            return True
        try:
            logger.info("Cargando Whisper 'base'... (primera vez puede tardar)")
            self._whisper_model = _whisper_lib.load_model(CONFIG["MODELO_WHISPER"])
            logger.info("Whisper 'base' listo.")
            return True
        except Exception as e:
            logger.error(f"Error cargando Whisper: {e}")
            return False

    def transcribir_audio(self, audio_path: str) -> tuple:
        """
        Transcribe un archivo de audio a texto usando Whisper.
        Devuelve (texto_transcrito, exito_bool).
        El audio_path debe ser un archivo WAV o MP3 temporal.
        """
        if not self.cargar_whisper():
            return "Whisper no disponible. Instala: pip install openai-whisper", False
        if not os.path.exists(audio_path):
            return f"Archivo de audio no encontrado: {audio_path}", False
        try:
            resultado = self._whisper_model.transcribe(
                audio_path,
                language="es",         # Forzamos español para mejor precision
                fp16=False             # fp16=False evita warnings en CPU/GPU sin soporte
            )
            texto = resultado.get("text", "").strip()
            if not texto:
                return "No se detectó audio claro.", False
            logger.info(f"Whisper transcribio: '{texto[:60]}'")
            return texto, True
        except Exception as e:
            logger.error(f"Error en transcripcion Whisper: {e}")
            return f"Error de transcripcion: {e}", False

    # ── RESUMEN Y CIERRE DE SESION ─────────────────────────────────────────────

    def generar_resumen_sesion(self) -> str:
        if not self.historial_sesion:
            return "Sesion sin contenido."
        historial_texto = ""
        for t in self.historial_sesion:
            historial_texto += f"Usuario: {t['user'][:400]}\nNexo: {t['nexo'][:600]}\n---\n"
        prompt = f"""
Resume esta conversacion de forma estructurada.
Devuelve solo el resumen, sin comentarios adicionales.

CONVERSACION:
{historial_texto}

Formato requerido:
TEMAS: [temas principales separados por coma]
DECISIONES: [decisiones tecnicas o conceptuales tomadas]
PENDIENTE: [preguntas o tareas sin resolver]
USUARIO_INFO: [datos detectados del usuario]
SINOPSIS: [2-3 frases con lo mas importante]
"""
        return self._llamar_ollama(prompt)

    def cerrar_sesion(self) -> str:
        if not self.historial_sesion:
            return "Sesion vacia, nada que guardar."

        resumen = self.generar_resumen_sesion()

        tags = ["historial"]
        for linea in resumen.split("\n"):
            if linea.startswith("TEMAS:"):
                raw_tags = linea.replace("TEMAS:", "").strip()
                tags    += [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
                break
        tags.append(self.sesion_inicio.strftime("sesion_%Y%m"))

        msg, ok = self.guardar_memoria(self.sesion_id, resumen, tags)
        if not ok:
            logger.error(f"Error guardando resumen de sesion: {msg}")

        self.actualizar_perfil_desde_sesion(resumen)
        self.historial_sesion = []

        return f"Sesion [{self.sesion_id}] guardada.\n\nResumen:\n{resumen}"

    # ── SYSTEM PROMPT Y CONSTRUCCION DE CONTEXTO ──────────────────────────────

    def construir_boot_context(self, pregunta: str = "") -> str:
        hw      = self._get_hw()
        perfil  = self.cargar_perfil()
        proyect = ", ".join(perfil.get("proyectos_activos", [])) or "ninguno"
        temas   = ", ".join(perfil.get("temas_frecuentes", [])[:8]) or "sin historial"
        modo    = "MODO CONCISO ACTIVADO: CPU alta, respuestas breves." if self._cpu_alta() else ""

        memorias_ctx = ""
        if pregunta:
            memorias_ctx_raw = self.recuperar_recuerdos(pregunta, top_k=3)
            if memorias_ctx_raw:
                memorias_ctx = f"=== MEMORIAS RECUPERADAS ===\n{memorias_ctx_raw}"

        perfil_texto = (
            f"Nombre: {perfil.get('nombre', 'Usuario')}\n"
            f"Hardware: {perfil.get('hardware', 'desconocido')}\n"
            f"Nivel Python: {perfil.get('nivel_python', 'desconocido')}\n"
            f"Otros: {json.dumps(perfil.get('nivel_otros', {}), ensure_ascii=False)}\n"
            f"Proyectos: {proyect}\n"
            f"Temas frecuentes: {temas}\n"
            f"Sesiones: {perfil.get('total_sesiones', 0)}\n"
            f"Ultima sesion: {perfil.get('ultima_sesion', 'primera vez')}\n"
            f"Preferencias: {perfil.get('preferencias_comunicacion', 'directo y tecnico')}"
        )

        return SYSTEM_PROMPT.format(
            nombre=perfil.get("nombre", "Usuario"),
            hardware=perfil.get("hardware", "desconocido"),
            plataforma="Windows" if IS_WINDOWS else "Linux/Mac",
            perfil_texto=perfil_texto,
            memorias_ctx=memorias_ctx,
        ) + (f"\n\n{modo}" if modo else "")

    def _construir_prompt_principal(self, pregunta: str, boot: str) -> str:
        hay_memorias = "MEMORIAS RECUPERADAS" in boot

        if hay_memorias:
            instruccion = (
                "Las memorias de arriba son tu contexto prioritario. "
                "Usaas cuando sean relevantes. Para lo demas, usa tu conocimiento completo."
            )
        else:
            instruccion = (
                "No hay memorias relevantes para esta pregunta. "
                "Responde con tu conocimiento completo. "
                "NO inventes recuerdos de conversaciones que no estan en el contexto."
            )

        historial = ""
        if self.historial_sesion:
            historial = "\n=== HISTORIAL DE ESTA SESION ===\n"
            for t in self.historial_sesion[-6:]:
                historial += f"Usuario: {t['user']}\nNexo: {t['nexo']}\n"

        return f"{boot}\n\n{historial}\n\n{instruccion}\n\nUsuario: {pregunta}\nNexo:".strip()

    # ── COMUNICACION CON OLLAMA ────────────────────────────────────────────────

    def _verificar_ollama(self) -> None:
        try:
            r = requests.get(CONFIG["OLLAMA_HEALTH"], timeout=3)
            if r.status_code == 200:
                modelos = [m.get("name", "") for m in r.json().get("models", [])]
                logger.info(f"Ollama online. Modelos: {modelos}")
                if CONFIG["MODELO_PRINCIPAL"] not in modelos and modelos:
                    logger.warning(
                        f"'{CONFIG['MODELO_PRINCIPAL']}' no encontrado. "
                        f"Disponibles: {modelos}. Ejecuta: ollama pull llama3.1"
                    )
        except requests.exceptions.ConnectionError:
            logger.error("Ollama NO responde. Ejecuta: ollama serve")
        except Exception as e:
            logger.warning(f"Verificacion Ollama con error: {e}")

    def _llamar_ollama(self, prompt: str) -> str:
        payload = {"model": CONFIG["MODELO_PRINCIPAL"], "prompt": prompt, "stream": False}
        try:
            r = requests.post(CONFIG["OLLAMA_ENDPOINT"], json=payload,
                              timeout=CONFIG["TIMEOUT_INFERENCIA"])
            r.raise_for_status()
            return r.json().get("response", "Respuesta vacia del modelo.")
        except requests.exceptions.ConnectionError:
            return "Ollama no responde. Ejecuta: ollama serve"
        except requests.exceptions.Timeout:
            return f"Timeout ({CONFIG['TIMEOUT_INFERENCIA']}s). Verifica que Llama este usando la GPU."
        except requests.exceptions.HTTPError as e:
            return f"Error HTTP de Ollama: {e}"
        except Exception as e:
            logger.error(f"Error inesperado en Ollama: {e}", exc_info=True)
            return "Error interno. Revisa nexo_audit.log."

    def _llamar_ollama_vision(self, prompt: str, imagen_b64: str) -> str:
        payload = {
            "model":  CONFIG["MODELO_VISION"],
            "prompt": prompt,
            "images": [imagen_b64],
            "stream": False
        }
        try:
            r = requests.post(CONFIG["OLLAMA_ENDPOINT"], json=payload, timeout=120)
            r.raise_for_status()
            return r.json().get("response", "Sin respuesta del modelo de vision.")
        except requests.exceptions.ConnectionError:
            return "Ollama no responde. Ejecuta: ollama serve"
        except requests.exceptions.Timeout:
            return "Timeout analizando imagen. Prueba con una imagen mas pequena."
        except requests.exceptions.HTTPError as e:
            if "404" in str(e):
                return "llama3.2-vision no instalado. Ejecuta: ollama pull llama3.2-vision"
            return f"Error HTTP vision: {e}"
        except Exception as e:
            logger.error(f"Error Ollama Vision: {e}", exc_info=True)
            return "Error interno procesando imagen. Revisa nexo_audit.log."

    # ── MOTOR DE INFERENCIA ────────────────────────────────────────────────────

    def despertar_nexo(self, pregunta: str, cliente: str = "local") -> str:
        try:
            self._check_rate_limit(cliente)
        except PermissionError as e:
            return str(e)
        try:
            pregunta = self._validar_query(pregunta)
        except ValueError as e:
            return f"Error: {e}"

        boot     = self.construir_boot_context(pregunta)
        prompt   = self._construir_prompt_principal(pregunta, boot)
        logger.info(f"[{cliente}] Query: '{pregunta[:60]}'")
        respuesta = self._llamar_ollama(prompt)
        self.historial_sesion.append({"user": pregunta, "nexo": respuesta})
        return respuesta

    # ── UTILIDADES ────────────────────────────────────────────────────────────

    def reparar_indices(self) -> str:
        try:
            archivos = os.listdir(self.db_path)
        except OSError as e:
            return f"Error leyendo DB: {e}"
        mds   = {f[:-3] for f in archivos if f.endswith(".md")}
        jsons = {f[:-5] for f in archivos if f.endswith(".json")}
        h_md  = mds - jsons
        h_js  = jsons - mds
        if not h_md and not h_js:
            return "Base de datos integra."
        informe = []
        if h_md: informe.append(f"Advertencia: .md sin .json: {h_md}")
        if h_js: informe.append(f"Advertencia: .json sin .md: {h_js}")
        return "\n".join(informe)

    def listar_memorias(self) -> list:
        metas = self._cargar_metadatos()
        resultado = [{
            "id":      m.get("id", "?"),
            "ts":      m.get("timestamp", "?")[:16],
            "tags":    m.get("tags", []),
            "preview": m.get("resumen", "")[:80],
            "kb":      round(m.get("bytes", 0) / 1000, 1)
        } for m in metas]
        return sorted(resultado, key=lambda x: x["ts"], reverse=True)


# ── CLI ────────────────────────────────────────────────────────────────────────

def cli():
    nexo   = NexoCompleto()
    perfil = nexo.cargar_perfil()

    print("\n" + "=" * 58)
    print(f"  NEXO v7.2 | Modelo: {CONFIG['MODELO_PRINCIPAL']}")
    print(f"  Windows: {IS_WINDOWS} | BM25: {BM25_OK} | Whisper: {WHISPER_OK}")
    print("  :ayuda para ver comandos")
    print("=" * 58)

    if perfil.get("total_sesiones", 0) > 0:
        print(f"\nBienvenido de vuelta, {perfil.get('nombre', 'Alex')}.")
        print(f"  Ultima sesion : {perfil.get('ultima_sesion', '?')}")
        print(f"  Total sesiones: {perfil.get('total_sesiones', 0)}")
    else:
        print("\nPrimera sesion. Nexo aprendera contigo.")
    print()

    while True:
        try:
            entrada = input("Tu -> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nCerrando sesion...")
            print(nexo.cerrar_sesion())
            break

        if not entrada:
            continue

        if entrada == ":ayuda":
            print(textwrap.dedent("""
            COMANDOS:
              :ayuda              - Esta ayuda
              :perfil             - Ver perfil actual
              :perfil set C V     - Actualizar campo C con valor V
              :memorias           - Listar memorias guardadas
              :guardar ID         - Guardar nueva memoria
              :buscar TEXTO       - Buscar memorias con BM25
              :reparar            - Verificar integridad DB
              :hw                 - Estado del hardware
              :salir              - Cerrar y guardar sesion
              :salir-rapido       - Salir sin guardar
            """))

        elif entrada == ":perfil":
            perfil = nexo.cargar_perfil()
            print("\n-- PERFIL --")
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
                print(f"\n-- {len(mems)} MEMORIAS --")
                for m in mems:
                    print(f"  [{m['id']}] {m['ts']} | {m['kb']}KB | {m['tags']}")
                    print(f"    {m['preview']}...")
            print()

        elif entrada.startswith(":guardar "):
            id_nuevo = entrada[len(":guardar "):].strip()
            print(f"Contenido para [{id_nuevo}] (linea vacia para terminar):")
            lineas = []
            while True:
                l = input("  > ")
                if l == "": break
                lineas.append(l)
            if lineas:
                tags_raw = input("Tags (coma): ")
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
                msg, ok = nexo.guardar_memoria(id_nuevo, "\n".join(lineas), tags)
                print(f"{'OK' if ok else 'ERROR'}: {msg}")

        elif entrada.startswith(":buscar "):
            q = entrada[len(":buscar "):].strip()
            resultado = nexo.recuperar_recuerdos(q)
            print(resultado if resultado else "Sin memorias relevantes.")

        elif entrada == ":reparar":
            print(nexo.reparar_indices())

        elif entrada == ":hw":
            print(nexo._get_hw())

        elif entrada == ":salir":
            print(nexo.cerrar_sesion())
            print("\nHasta la proxima.")
            break

        elif entrada == ":salir-rapido":
            print("Saliendo sin guardar.")
            break

        else:
            print("Nexo -> ", end="", flush=True)
            print(nexo.despertar_nexo(entrada))
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexo de Consciencia v7.2")
    parser.add_argument("--setup", action="store_true",
                        help="Descarga recursos de NLTK y Whisper")
    args = parser.parse_args()

    if args.setup:
        try:
            import nltk
            print("Descargando recursos NLTK...")
            nltk.download("punkt",     quiet=True)
            nltk.download("stopwords", quiet=True)
            print("NLTK OK.")
        except ImportError:
            print("nltk no instalado: pip install nltk")

        if WHISPER_OK:
            print("Pre-cargando Whisper 'base'...")
            nexo_tmp = NexoCompleto.__new__(NexoCompleto)
            nexo_tmp._whisper_model = None
            nexo_tmp.cargar_whisper()
            print("Whisper OK.")
        else:
            print("Whisper no instalado: pip install openai-whisper")

        print("\nSetup completado. Ejecuta: py -3.11 nexo_consciencia_v7_2.py")
    else:
        cli()