""""
╔══════════════════════════════════════════════════════════════════════════════╗
║  NEXO DE CONSCIENCIA v7.1 — MULTIMODAL EDITION                             ║
║  Autor original : AlexMedran-exe                                           ║
║  Dashboard      : Claude (Anthropic)                                       ║
║                                                                              ║
║  NOVEDADES v7.1 respecto a v7.0:                                           ║
║    ✅ Ingesta de PDFs nativos (texto extraído con pymupdf)                  ║
║    ✅ Ingesta de imágenes/capturas (descripción via llama3.2-vision)        ║
║    ✅ Chunking inteligente para PDFs largos                                 ║
║    ✅ Pestaña dedicada "📎 Documentos" para todo lo multimedia              ║
║    ✅ Toda la funcionalidad de v7.0 intacta                                 ║
║                                                                              ║
║  INSTALACIÓN NUEVA DEPENDENCIA:                                             ║
║    py -3.11 -m pip install pymupdf                                         ║
║                                                                              ║
║  MODELO DE VISIÓN (instalar una vez en Ollama):                            ║
║    ollama pull llama3.2-vision                                             ║
║    (pesa ~7GB, tu llama3.1 se queda intacto)                               ║
║                                                                              ║
║  ARRANQUE:                                                                  ║
║    py -3.11 -m streamlit run nexo_dashboard_v7_1.py                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import base64
import io
import streamlit as st
import psutil
import requests
from nexo_consciencia_v6_2 import NexoCompleto, CONFIG, escribir_atomico

# ── Importación condicional de pymupdf ───────────────────────────────────────
# Si no está instalado el dashboard sigue funcionando, solo desactiva los PDFs
try:
    import fitz  # pymupdf
    PYMUPDF_OK = True
except ImportError:
    PYMUPDF_OK = False

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="NEXO v7.1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    .stChatMessage p { font-size: 0.95rem; line-height: 1.65; }
    .badge-chat {
        display:inline-block; padding:3px 12px; border-radius:12px;
        font-size:0.8rem; font-weight:700;
        background:#1e3a5f; color:#60a5fa; border:1px solid #60a5fa;
    }
    .badge-nexo {
        display:inline-block; padding:3px 12px; border-radius:12px;
        font-size:0.8rem; font-weight:700;
        background:#3a1f5f; color:#c084fc; border:1px solid #c084fc;
    }
    .badge-doc {
        display:inline-block; padding:3px 12px; border-radius:12px;
        font-size:0.8rem; font-weight:700;
        background:#3a2a10; color:#fb923c; border:1px solid #fb923c;
    }
    .diario-activo {
        background:#1a3a1a; border:1px solid #4ade80;
        border-radius:6px; padding:6px 10px; margin:3px 0;
        font-size:0.82rem; color:#4ade80;
    }
    .diario-inactivo {
        background:#111827; border:1px solid #374151;
        border-radius:6px; padding:6px 10px; margin:3px 0;
        font-size:0.82rem; color:#9ca3af;
    }
    .section-title {
        font-size:0.7rem; font-weight:700; letter-spacing:0.1em;
        color:#6b7280; text-transform:uppercase; margin:12px 0 4px 0;
    }
    .chunk-info {
        background:#1a2a1a; border-left:3px solid #4ade80;
        padding:6px 10px; margin:4px 0; font-size:0.8rem;
        border-radius:0 4px 4px 0;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  INICIALIZACIÓN
# ══════════════════════════════════════════════════════════════════════════════

def init_state():
    if "nexo" not in st.session_state:
        st.session_state.nexo = NexoCompleto()
    if "modo" not in st.session_state:
        st.session_state.modo = "chat"
    if "historial_chat" not in st.session_state:
        st.session_state.historial_chat = []
    if "historial_nexo" not in st.session_state:
        st.session_state.historial_nexo = []
    if "diarios_seleccionados" not in st.session_state:
        st.session_state.diarios_seleccionados = set()
    if "diario_inspeccionado" not in st.session_state:
        st.session_state.diario_inspeccionado = None

init_state()
nexo: NexoCompleto = st.session_state.nexo


# ══════════════════════════════════════════════════════════════════════════════
#  FUNCIONES DE INGESTA MULTIMEDIA
# ══════════════════════════════════════════════════════════════════════════════

def extraer_texto_pdf(archivo_bytes: bytes) -> tuple:
    """
    Extrae todo el texto de un PDF usando pymupdf (fitz).

    Devuelve (texto_completo, num_paginas, num_palabras).

    pymupdf es la librería más rápida y precisa para extracción de texto
    de PDFs nativos (con texto seleccionable). Para PDFs escaneados
    (imágenes sin texto) devuelve string vacío — esos necesitarían OCR.

    No usamos pdfplumber ni PyPDF2 porque pymupdf tiene mejor precisión
    con layouts complejos (columnas, tablas, cabeceras).
    """
    if not PYMUPDF_OK:
        return "", 0, 0

    try:
        # Abrir el PDF desde bytes en memoria (sin escribir en disco)
        doc = fitz.open(stream=archivo_bytes, filetype="pdf")
        paginas_texto = []

        for num_pag, pagina in enumerate(doc, start=1):
            texto_pagina = pagina.get_text("text")  # Extracción texto plano
            if texto_pagina.strip():
                # Añadimos marcador de página para que el modelo sepa la ubicación
                paginas_texto.append(f"[PÁGINA {num_pag}]\n{texto_pagina.strip()}")

        doc.close()

        texto_total = "\n\n".join(paginas_texto)
        num_palabras = len(texto_total.split())
        return texto_total, len(paginas_texto), num_palabras

    except Exception as e:
        return f"Error extrayendo PDF: {e}", 0, 0


def chunkear_texto(texto: str, chunk_size: int = 1500, overlap: int = 200) -> list:
    """
    Divide texto largo en chunks solapados para que BM25 funcione bien.

    POR QUÉ CHUNKING:
    Si un PDF tiene 10.000 palabras y lo guardamos como un solo diario,
    el snippet de 1000 chars que usa BM25 para indexar solo cubre el inicio.
    El resto del documento es invisible para la recuperación.

    Con chunking cada fragmento tiene su propio índice BM25, así que
    el sistema puede recuperar información de cualquier parte del PDF.

    POR QUÉ OVERLAP:
    Si una idea importante está justo en el corte entre dos chunks,
    el solapamiento garantiza que aparece completa en al menos uno de ellos.

    PARÁMETROS:
    - chunk_size: palabras por chunk (~1500 palabras ≈ 1 página A4 densa)
    - overlap: palabras que se repiten entre chunks consecutivos
    """
    palabras = texto.split()
    if len(palabras) <= chunk_size:
        return [texto]  # Documento corto: un solo chunk

    chunks = []
    inicio = 0
    while inicio < len(palabras):
        fin = min(inicio + chunk_size, len(palabras))
        chunk_palabras = palabras[inicio:fin]
        chunks.append(" ".join(chunk_palabras))
        if fin == len(palabras):
            break
        inicio = fin - overlap  # Retrocedemos el overlap para el siguiente chunk

    return chunks


def ingestar_pdf(
    archivo_bytes: bytes,
    nombre_base: str,
    tags_extra: list,
    chunk_size: int = 1500
) -> dict:
    """
    Pipeline completo de ingesta de PDF:
      1. Extrae texto con pymupdf
      2. Divide en chunks si es largo
      3. Guarda cada chunk como diario separado con ID numerado
      4. Devuelve resumen de la operación

    Los IDs de los chunks siguen el patrón: nombre_base_p01, nombre_base_p02...
    Así en el sidebar aparecen agrupados y es fácil seleccionarlos todos
    en el Modo Nexo cuando quieres contexto completo del documento.
    """
    texto, num_pags, num_palabras = extraer_texto_pdf(archivo_bytes)

    if not texto or texto.startswith("Error"):
        return {"ok": False, "error": texto or "PDF vacío o sin texto seleccionable."}

    chunks = chunkear_texto(texto, chunk_size=chunk_size)
    tags = ["pdf", "documento"] + tags_extra
    ids_guardados = []

    for i, chunk in enumerate(chunks, start=1):
        # ID con cero por delante para orden alfabético correcto (p01, p02... p10)
        id_chunk = f"{nombre_base}_p{str(i).zfill(2)}"
        cabecera = f"DOCUMENTO PDF: {nombre_base}\nChunk {i} de {len(chunks)}\n\n"
        try:
            nexo.guardar_memoria(id_chunk, cabecera + chunk, tags)
            ids_guardados.append(id_chunk)
        except ValueError as e:
            return {"ok": False, "error": f"Error en chunk {i}: {e}"}

    return {
        "ok":        True,
        "paginas":   num_pags,
        "palabras":  num_palabras,
        "chunks":    len(chunks),
        "ids":       ids_guardados,
    }


def describir_imagen_con_vision(imagen_bytes: bytes, media_type: str, instruccion: str = "") -> str:
    """
    Manda una imagen al modelo llama3.2-vision de Ollama y devuelve su descripción.

    CÓMO FUNCIONA:
    Ollama acepta imágenes en base64 dentro del campo 'images' del payload.
    El modelo las procesa junto con el prompt y genera una descripción textual.

    Esa descripción es lo que guardamos como diario: no la imagen en sí,
    sino lo que el modelo "vio" en ella. Esto permite que BM25 indexe
    el contenido visual como si fuera texto normal.

    PARÁMETROS:
    - imagen_bytes: bytes de la imagen (PNG, JPG, WEBP)
    - media_type: "image/png", "image/jpeg", etc.
    - instruccion: prompt personalizado del usuario ("¿qué error muestra esta captura?")
    """
    # Convertir imagen a base64
    imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")

    prompt_vision = instruccion if instruccion.strip() else (
        "Describe esta imagen en detalle en español. "
        "Si contiene texto, transcríbelo completo. "
        "Si es código, inclúyelo íntegro. "
        "Si es un diagrama o captura de pantalla, describe cada elemento visible. "
        "Sé exhaustivo: esta descripción se usará como memoria para futuras consultas."
    )

    payload = {
        "model":  "llama3.2-vision",
        "prompt": prompt_vision,
        "images": [imagen_b64],   # Ollama espera lista de imágenes en base64
        "stream": False
    }

    try:
        r = requests.post(
            CONFIG["OLLAMA_ENDPOINT"],
            json=payload,
            timeout=120  # Las imágenes tardan más que texto puro
        )
        r.raise_for_status()
        return r.json().get("response", "Sin respuesta del modelo de visión.")
    except requests.exceptions.ConnectionError:
        return "❌ Ollama no responde. ¿Está corriendo? → ollama serve"
    except requests.exceptions.Timeout:
        return "⏱️ Timeout procesando imagen. Prueba con una imagen más pequeña."
    except Exception as e:
        # Error común: el modelo no está instalado
        if "model" in str(e).lower() or "404" in str(e):
            return "❌ llama3.2-vision no está instalado. Ejecuta: ollama pull llama3.2-vision"
        return f"❌ Error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS (mismos que v7.0)
# ══════════════════════════════════════════════════════════════════════════════

def cambiar_modo(nuevo_modo: str):
    st.session_state.modo = nuevo_modo
    if nuevo_modo == "chat":
        nexo.historial_sesion = st.session_state.historial_chat
    else:
        nexo.historial_sesion = st.session_state.historial_nexo

def guardar_chat_como_diario(nombre_id: str, tags_extra: list = []):
    if not st.session_state.historial_chat:
        return "⚠️ El chat está vacío."
    try:
        nexo._validar_id(nombre_id)
    except ValueError as e:
        return f"❌ {e}"
    import datetime
    contenido = f"CHAT GUARDADO: {nombre_id}\nFecha: {datetime.datetime.now()}\n\n"
    for t in st.session_state.historial_chat:
        contenido += f"Alex: {t['user']}\nNexo: {t['nexo']}\n---\n"
    try:
        return nexo.guardar_memoria(nombre_id, contenido, ["chat"] + tags_extra)
    except ValueError as e:
        return f"❌ {e}"

def construir_prompt_nexo_fusionado(pregunta: str, ids_seleccionados: set) -> str:
    perfil = nexo.cargar_perfil()
    bloque_fusion = ""
    ids_cargados = []
    for id_diario in ids_seleccionados:
        path = os.path.join(nexo.db_path, f"{id_diario}.md")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    contenido = f.read()
                bloque_fusion += f"\n{'='*40}\nCONTEXTO DE: {id_diario}\n{'='*40}\n{contenido}\n"
                ids_cargados.append(id_diario)
            except IOError:
                pass
    historial_texto = ""
    if st.session_state.historial_nexo:
        historial_texto = "\n--- CONVERSACIÓN ACTUAL ---\n"
        for t in st.session_state.historial_nexo[-6:]:
            historial_texto += f"Alex: {t['user']}\nNexo: {t['nexo']}\n"
    return f"""
Eres 'Nexo', el asistente de IA local de {perfil.get('nombre', 'Alex')}.
Hardware: {perfil.get('hardware', 'Acer Nitro')}.

MODO NEXO FUSIONADO — Tienes contexto de {len(ids_cargados)} fuente(s): {ids_cargados}
Usa este contexto como si hubieras participado en todas esas conversaciones y documentos.
Para preguntas generales usa tu conocimiento completo como Llama 3.1.
Responde en español, estilo directo y técnico.

{'--- CONTEXTO FUSIONADO ---' + bloque_fusion if bloque_fusion else '(Sin diarios: responde con conocimiento general)'}

{historial_texto}

Alex: {pregunta}
Nexo:""".strip()

def llamar_modelo_modo_nexo(pregunta: str) -> str:
    try:
        pregunta = nexo._validar_query(pregunta)
    except ValueError as e:
        return f"Error: {e}"
    nexo._rl["streamlit_nexo"] = 0
    prompt = construir_prompt_nexo_fusionado(pregunta, st.session_state.diarios_seleccionados)
    respuesta = nexo._llamar_ollama(prompt)
    st.session_state.historial_nexo.append({"user": pregunta, "nexo": respuesta})
    return respuesta


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    modo_actual = st.session_state.modo
    if modo_actual == "chat":
        st.markdown('<div class="badge-chat">💬 MODO CHAT</div>', unsafe_allow_html=True)
    elif modo_actual == "nexo":
        st.markdown('<div class="badge-nexo">🧬 MODO NEXO</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="badge-doc">📎 DOCUMENTOS</div>', unsafe_allow_html=True)

    st.title("🧠 NEXO v7.1")

    # Selección de modo
    st.markdown('<div class="section-title">Modo de conversación</div>', unsafe_allow_html=True)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("💬 Chat", use_container_width=True,
                     type="primary" if modo_actual == "chat" else "secondary"):
            cambiar_modo("chat")
            st.rerun()
    with col_m2:
        if st.button("🧬 Nexo", use_container_width=True,
                     type="primary" if modo_actual == "nexo" else "secondary"):
            cambiar_modo("nexo")
            st.rerun()

    if modo_actual == "chat":
        st.caption("Conversación independiente. Sin contexto de otros chats.")
    else:
        n_sel = len(st.session_state.diarios_seleccionados)
        st.caption(f"Contexto fusionado. {n_sel} diario(s) activo(s).")

    st.divider()

    # ── Biblioteca de diarios con secciones colapsables por tipo ───────────────
    #
    # DISEÑO:
    # Cada tipo (Chats, PDFs, Imágenes, Otros) tiene su propia sección con:
    #   - Botón cabecera que expande/colapsa la sección
    #   - Checkbox "Marcar todos" para seleccionar el grupo de golpe
    #   - Lista de items con checkbox individual + botón de preview
    #
    # Usamos st.session_state para controlar qué secciones están abiertas
    # en lugar de st.expander, porque st.expander dentro del sidebar con
    # checkboxes tiene un bug conocido de Streamlit que provoca rerenders
    # infinitos cuando hay muchos items.
    #
    st.markdown('<div class="section-title">Biblioteca</div>', unsafe_allow_html=True)
    mems    = nexo.listar_memorias()
    diarios = [m for m in mems if "historial" not in m.get("tags", [])]

    # Inicializar estado de secciones abiertas/cerradas
    if "secciones_abiertas" not in st.session_state:
        st.session_state.secciones_abiertas = {
            "chats":    True,   # Chats abierto por defecto
            "pdfs":     True,
            "imagenes": True,
            "otros":    False,  # Otros cerrado por defecto (menos frecuente)
        }

    if not diarios:
        st.caption("Sin diarios. Guarda un chat o sube un PDF.")
    else:
        # Agrupar por tipo
        grupos = {
            "chats":    {"icono": "💬", "label": "Chats",    "items": []},
            "pdfs":     {"icono": "📄", "label": "PDFs",     "items": []},
            "imagenes": {"icono": "🖼️", "label": "Imágenes", "items": []},
            "otros":    {"icono": "📖", "label": "Otros",    "items": []},
        }
        for d in diarios:
            tags = d.get("tags", [])
            if "chat"   in tags: grupos["chats"]["items"].append(d)
            elif "pdf"  in tags: grupos["pdfs"]["items"].append(d)
            elif "imagen" in tags: grupos["imagenes"]["items"].append(d)
            else:                grupos["otros"]["items"].append(d)

        for grupo_id, grupo in grupos.items():
            items = grupo["items"]
            if not items:
                continue  # No mostrar secciones vacías

            abierto = st.session_state.secciones_abiertas.get(grupo_id, True)
            n_items = len(items)
            n_sel_grupo = sum(1 for d in items if d["id"] in st.session_state.diarios_seleccionados)
            flecha = "▼" if abierto else "▶"

            # ── Cabecera de sección (botón toggle) ──────────────────────────
            col_hdr, col_all = st.sidebar.columns([0.75, 0.25])
            with col_hdr:
                label_hdr = f"{flecha} {grupo['icono']} {grupo['label']} ({n_items})"
                if n_sel_grupo > 0:
                    label_hdr += f" ✓{n_sel_grupo}"
                if st.button(label_hdr, key=f"hdr_{grupo_id}", use_container_width=True):
                    st.session_state.secciones_abiertas[grupo_id] = not abierto
                    st.rerun()
            with col_all:
                # Botón "marcar todos" / "desmarcar todos" del grupo
                todos_marcados = all(d["id"] in st.session_state.diarios_seleccionados for d in items)
                label_all = "✓ All" if not todos_marcados else "✗ All"
                if st.button(label_all, key=f"all_{grupo_id}", use_container_width=True,
                             help="Marcar/desmarcar todos los de este grupo"):
                    if todos_marcados:
                        for d in items:
                            st.session_state.diarios_seleccionados.discard(d["id"])
                    else:
                        for d in items:
                            st.session_state.diarios_seleccionados.add(d["id"])
                    st.rerun()

            # ── Items de la sección (solo si está abierta) ──────────────────
            if abierto:
                for d in items:
                    esta_sel = d["id"] in st.session_state.diarios_seleccionados
                    col_ck, col_inf = st.columns([0.15, 0.85])
                    with col_ck:
                        nuevo_val = st.checkbox(
                            "", value=esta_sel,
                            key=f"check_{d['id']}",
                            help=f"Incluir en Modo Nexo"
                        )
                        if nuevo_val != esta_sel:
                            if nuevo_val:
                                st.session_state.diarios_seleccionados.add(d["id"])
                            else:
                                st.session_state.diarios_seleccionados.discard(d["id"])
                            st.rerun()
                    with col_inf:
                        # Nombre acortado si es muy largo (chunks de PDF tienen nombres largos)
                        nombre_display = d["id"] if len(d["id"]) <= 18 else d["id"][:16] + "…"
                        if st.button(
                            nombre_display,
                            key=f"btn_{d['id']}",
                            use_container_width=True,
                            help=d["id"]  # Tooltip con nombre completo
                        ):
                            st.session_state.diario_inspeccionado = (
                                None if st.session_state.diario_inspeccionado == d["id"]
                                else d["id"]
                            )
                            st.rerun()

            st.markdown("&nbsp;", unsafe_allow_html=True)  # Separación entre grupos

    # Preview del diario inspeccionado
    if st.session_state.diario_inspeccionado:
        did = st.session_state.diario_inspeccionado
        path_md = os.path.join(nexo.db_path, f"{did}.md")
        st.markdown(f"**Preview: {did}**")
        if os.path.exists(path_md):
            with open(path_md, "r", encoding="utf-8") as f:
                contenido_prev = f.read()
            st.text_area("", contenido_prev[:500] + ("..." if len(contenido_prev) > 500 else ""),
                         height=130, disabled=True, label_visibility="collapsed")
        if st.button("✕ Cerrar", use_container_width=True):
            st.session_state.diario_inspeccionado = None
            st.rerun()

    st.divider()

    # Telemetría
    st.markdown('<div class="section-title">Hardware</div>', unsafe_allow_html=True)
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        st.progress(cpu / 100, text=f"CPU {cpu:.0f}%")
        st.progress(ram / 100, text=f"RAM {ram:.0f}%")
        bat = psutil.sensors_battery()
        if bat:
            st.progress(bat.percent / 100, text=f"🔋 {bat.percent:.0f}%")
        else:
            st.caption("⚡ AC")
    except Exception:
        st.caption("Telemetría N/A")

    st.divider()

    # Acciones
    st.markdown('<div class="section-title">Acciones</div>', unsafe_allow_html=True)
    if st.button("🗑️ Limpiar pantalla", use_container_width=True):
        if modo_actual == "chat":
            st.session_state.historial_chat = []
            nexo.historial_sesion = []
        else:
            st.session_state.historial_nexo = []
        st.rerun()

    if st.button("💾 Guardar sesión", use_container_width=True, type="primary"):
        nexo.historial_sesion = (
            st.session_state.historial_chat
            if modo_actual == "chat"
            else st.session_state.historial_nexo
        )
        if nexo.historial_sesion:
            with st.spinner("Generando resumen..."):
                nexo.cerrar_sesion()
            st.success("Sesión guardada.")
            if modo_actual == "chat":
                st.session_state.historial_chat = []
            else:
                st.session_state.historial_nexo = []
            nexo.historial_sesion = []
            st.rerun()
        else:
            st.warning("Sesión vacía.")

    perfil = nexo.cargar_perfil()
    st.caption(f"👤 {perfil.get('nombre', 'Alex')} · {perfil.get('total_sesiones', 0)} sesiones")


# ══════════════════════════════════════════════════════════════════════════════
#  TABS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════════════

tab_chat, tab_nexo, tab_docs, tab_diarios, tab_sesiones = st.tabs([
    "💬 Chat",
    "🧬 Nexo",
    "📎 Documentos",
    "📂 Diarios",
    "📋 Sesiones"
])


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 1: CHAT INDEPENDIENTE
# ══════════════════════════════════════════════════════════════════════════════

with tab_chat:
    st.title("💬 Chat Independiente")
    st.caption("Sin contexto de otros chats. Guárdalo al terminar para convertirlo en diario.")

    nexo.historial_sesion = st.session_state.historial_chat

    if not st.session_state.historial_chat:
        st.info("💡 Chat vacío. Escribe algo para empezar.")

    for turno in st.session_state.historial_chat:
        with st.chat_message("user"):    st.markdown(turno["user"])
        with st.chat_message("assistant"): st.markdown(turno["nexo"])

    if prompt_chat := st.chat_input("Escribe tu mensaje...", key="input_chat"):
        with st.chat_message("user"):
            st.markdown(prompt_chat)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                nexo._rl["streamlit"] = 0
                respuesta_chat = nexo.despertar_nexo(prompt_chat, cliente="streamlit")
                st.markdown(respuesta_chat)
        st.session_state.historial_chat = nexo.historial_sesion.copy()
        st.rerun()

    if st.session_state.historial_chat:
        st.divider()
        st.subheader("💾 Guardar como diario")
        col_id, col_tags, col_btn = st.columns([2, 2, 1])
        with col_id:
            nombre_d = st.text_input("Nombre", placeholder="java_tareas", key="nomb_chat")
        with col_tags:
            tags_d = st.text_input("Tags", placeholder="java, universidad", key="tags_chat")
        with col_btn:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            if st.button("Guardar", type="primary", use_container_width=True):
                if nombre_d:
                    tags_l = [t.strip() for t in tags_d.split(",") if t.strip()]
                    msg = guardar_chat_como_diario(nombre_d, tags_l)
                    if msg.startswith("✅"):
                        st.success(f"{msg} — Disponible en la Biblioteca.")
                        st.session_state.historial_chat = []
                        nexo.historial_sesion = []
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Escribe un nombre.")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 2: MODO NEXO
# ══════════════════════════════════════════════════════════════════════════════

with tab_nexo:
    st.title("🧬 Modo Nexo")
    n_sel = len(st.session_state.diarios_seleccionados)
    if n_sel > 0:
        st.success(f"**Contexto activo:** {', '.join(sorted(st.session_state.diarios_seleccionados))}")
    else:
        st.warning("Sin diarios seleccionados. Marca uno o más en la Biblioteca (sidebar).")

    if not st.session_state.historial_nexo:
        st.info("💡 Selecciona diarios en el sidebar y empieza a hablar.")

    for turno in st.session_state.historial_nexo:
        with st.chat_message("user"):    st.markdown(turno["user"])
        with st.chat_message("assistant"): st.markdown(turno["nexo"])

    if prompt_nexo := st.chat_input("Habla con el Nexo...", key="input_nexo"):
        with st.chat_message("user"):
            st.markdown(prompt_nexo)
        with st.chat_message("assistant"):
            with st.spinner(f"Consultando {n_sel} diario(s)..."):
                respuesta_nexo = llamar_modelo_modo_nexo(prompt_nexo)
                st.markdown(respuesta_nexo)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 3: DOCUMENTOS (PDF + IMÁGENES) — NUEVO EN v7.1
# ══════════════════════════════════════════════════════════════════════════════

with tab_docs:
    st.title("📎 Ingestar Documentos")
    st.caption(
        "Convierte PDFs e imágenes en diarios que el Nexo puede usar como contexto. "
        "Una vez procesados aparecen en la Biblioteca igual que cualquier otro diario."
    )

    sub_pdf, sub_img = st.tabs(["📄 PDF", "🖼️ Imagen / Captura"])

    # ── SUB-TAB PDF ──────────────────────────────────────────────────────────
    with sub_pdf:
        if not PYMUPDF_OK:
            st.error(
                "pymupdf no está instalado. Ejecuta:\n\n"
                "```\npy -3.11 -m pip install pymupdf\n```\n\n"
                "Luego reinicia el dashboard."
            )
        else:
            st.subheader("📄 Subir PDF")
            st.caption(
                "Funciona con PDFs nativos (texto seleccionable): apuntes exportados, "
                "documentación, papers, contratos. "
                "PDFs escaneados sin texto no funcionan aquí."
            )

            col_up, col_cfg = st.columns([1, 1])

            with col_up:
                archivo_pdf = st.file_uploader(
                    "Selecciona un PDF",
                    type=["pdf"],
                    help="Máximo recomendado: 50MB"
                )
                if archivo_pdf:
                    st.success(f"Archivo cargado: **{archivo_pdf.name}** ({archivo_pdf.size // 1000}KB)")

            with col_cfg:
                nombre_pdf = st.text_input(
                    "Nombre base del diario",
                    placeholder="apuntes_java",
                    help="Los chunks se guardarán como apuntes_java_p01, apuntes_java_p02..."
                )
                tags_pdf = st.text_input(
                    "Tags adicionales",
                    placeholder="universidad, java, teoria"
                )
                chunk_size = st.slider(
                    "Tamaño de chunk (palabras)",
                    min_value=500,
                    max_value=3000,
                    value=1500,
                    step=250,
                    help="Chunks más pequeños = más precisión en recuperación. "
                         "Chunks más grandes = más contexto por respuesta."
                )

            if archivo_pdf and nombre_pdf:
                if st.button("⚙️ Procesar e ingestar PDF", type="primary", use_container_width=True):
                    tags_lista = [t.strip() for t in tags_pdf.split(",") if t.strip()]

                    with st.spinner("Extrayendo texto y creando diarios..."):
                        resultado = ingestar_pdf(
                            archivo_pdf.getvalue(),
                            nombre_pdf,
                            tags_lista,
                            chunk_size=chunk_size
                        )

                    if resultado["ok"]:
                        st.success(
                            f"✅ PDF procesado correctamente.\n\n"
                            f"- **Páginas:** {resultado['paginas']}\n"
                            f"- **Palabras:** {resultado['palabras']:,}\n"
                            f"- **Chunks creados:** {resultado['chunks']}"
                        )
                        st.markdown("**Diarios creados en la Biblioteca:**")
                        for id_chunk in resultado["ids"]:
                            st.markdown(
                                f'<div class="chunk-info">📄 {id_chunk}</div>',
                                unsafe_allow_html=True
                            )
                        st.info(
                            "💡 Para usar este PDF en el Modo Nexo, marca sus chunks "
                            "en la Biblioteca (sidebar). Marca todos los _p0X del mismo "
                            "nombre para tener el documento completo."
                        )
                        st.rerun()
                    else:
                        st.error(f"Error: {resultado['error']}")
            elif archivo_pdf and not nombre_pdf:
                st.warning("Escribe un nombre para el diario antes de procesar.")

    # ── SUB-TAB IMAGEN ────────────────────────────────────────────────────────
    with sub_img:
        st.subheader("🖼️ Subir imagen o captura de pantalla")
        st.caption(
            "El modelo llama3.2-vision analiza la imagen y genera una descripción textual "
            "que se guarda como diario. Útil para capturas de errores, diagramas, "
            "apuntes escritos a mano, o cualquier contenido visual."
        )

        # Aviso si llama3.2-vision no está instalado
        st.info(
            "📦 Requiere **llama3.2-vision** en Ollama. Si no lo tienes:\n\n"
            "```\nollama pull llama3.2-vision\n```\n\n"
            "Pesa ~7GB. Tu llama3.1 se queda intacto.",
            icon="ℹ️"
        )

        col_img_up, col_img_cfg = st.columns([1, 1])

        with col_img_up:
            archivo_img = st.file_uploader(
                "Selecciona imagen",
                type=["png", "jpg", "jpeg", "webp"],
                help="PNG, JPG o WEBP. Capturas de pantalla, fotos, diagramas."
            )
            if archivo_img:
                # Mostrar preview de la imagen subida
                st.image(archivo_img, caption=archivo_img.name, use_column_width=True)

        with col_img_cfg:
            nombre_img = st.text_input(
                "Nombre del diario",
                placeholder="error_java_npe",
                key="nombre_img"
            )
            tags_img = st.text_input(
                "Tags",
                placeholder="error, java, debug",
                key="tags_img"
            )
            instruccion_img = st.text_area(
                "Instrucción para el modelo (opcional)",
                placeholder="¿Qué error muestra esta captura? / Describe el diagrama / Transcribe el texto...",
                height=100,
                help="Deja vacío para descripción general automática."
            )

        if archivo_img and nombre_img:
            if st.button("🔍 Analizar imagen con IA", type="primary", use_container_width=True):
                # Determinar media type
                ext = archivo_img.name.split(".")[-1].lower()
                media_type_map = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "webp": "image/webp"
                }
                media_type = media_type_map.get(ext, "image/png")

                with st.spinner("El modelo está analizando la imagen... (puede tardar 20-60s)"):
                    descripcion = describir_imagen_con_vision(
                        archivo_img.getvalue(),
                        media_type,
                        instruccion_img
                    )

                if descripcion.startswith("❌") or descripcion.startswith("⏱️"):
                    st.error(descripcion)
                else:
                    st.markdown("**Descripción generada por el modelo:**")
                    st.text_area("", descripcion, height=200,
                                 disabled=True, label_visibility="collapsed")

                    # Guardar como diario
                    tags_lista_img = [t.strip() for t in tags_img.split(",") if t.strip()]
                    contenido_img = (
                        f"IMAGEN ANALIZADA: {nombre_img}\n"
                        f"Archivo original: {archivo_img.name}\n\n"
                        f"DESCRIPCIÓN DEL MODELO:\n{descripcion}"
                    )
                    try:
                        msg = nexo.guardar_memoria(
                            nombre_img,
                            contenido_img,
                            ["imagen"] + tags_lista_img
                        )
                        st.success(f"{msg} — Disponible en la Biblioteca.")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error guardando: {e}")
        elif archivo_img and not nombre_img:
            st.warning("Escribe un nombre para el diario.")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 4: GESTIÓN DE DIARIOS
# ══════════════════════════════════════════════════════════════════════════════

with tab_diarios:
    st.subheader("📂 Gestión de Diarios")

    with st.expander("➕ Crear diario manual", expanded=False):
        col_da, col_db = st.columns(2)
        with col_da:
            new_id_m = st.text_input("ID", placeholder="conocimientos_java")
            new_tags_m = st.text_input("Tags", placeholder="java, teoria")
        with col_db:
            new_content_m = st.text_area("Contenido", height=120)
        if st.button("💾 Guardar diario manual", type="primary"):
            if new_id_m and new_content_m:
                try:
                    tags_m = [t.strip() for t in new_tags_m.split(",") if t.strip()]
                    st.success(nexo.guardar_memoria(new_id_m, new_content_m, tags_m))
                    st.rerun()
                except ValueError as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("ID y contenido obligatorios.")

    st.divider()

    mems_tab    = nexo.listar_memorias()
    diarios_tab = [m for m in mems_tab if "historial" not in m.get("tags", [])]

    if not diarios_tab:
        st.info("No hay diarios. Guarda un chat, sube un PDF o una imagen.")
    else:
        # Agrupar por tipo para mejor visualización
        pdfs_tab    = [d for d in diarios_tab if "pdf"    in d.get("tags", [])]
        imgs_tab    = [d for d in diarios_tab if "imagen" in d.get("tags", [])]
        chats_tab   = [d for d in diarios_tab if "chat"   in d.get("tags", [])]
        otros_tab   = [d for d in diarios_tab
                       if not any(t in d.get("tags", []) for t in ["pdf", "imagen", "chat"])]

        def mostrar_grupo(titulo: str, items: list, icono: str):
            if not items:
                return
            st.markdown(f"**{icono} {titulo} ({len(items)})**")
            for d in items:
                marcado = "☑" if d["id"] in st.session_state.diarios_seleccionados else "☐"
                st.markdown(
                    f"`{marcado}` **{d['id']}** · {d['ts']} · {d['kb']}KB · "
                    f"`{', '.join(d['tags'])}`"
                )

        mostrar_grupo("PDFs", pdfs_tab, "📄")
        mostrar_grupo("Imágenes", imgs_tab, "🖼️")
        mostrar_grupo("Chats guardados", chats_tab, "💬")
        mostrar_grupo("Otros", otros_tab, "📖")

        st.divider()
        ids_todos = [d["id"] for d in diarios_tab]
        sel_d = st.selectbox("Ver contenido completo de:", ["— selecciona —"] + ids_todos)
        if sel_d != "— selecciona —":
            path_c = os.path.join(nexo.db_path, f"{sel_d}.md")
            if os.path.exists(path_c):
                with open(path_c, "r", encoding="utf-8") as f:
                    cont_c = f.read()
                st.text_area("", cont_c, height=350, disabled=True, label_visibility="collapsed")
                st.caption(f"{len(cont_c)} caracteres · {len(cont_c.encode())} bytes")


# ══════════════════════════════════════════════════════════════════════════════
#  TAB 5: SESIONES GUARDADAS
# ══════════════════════════════════════════════════════════════════════════════

with tab_sesiones:
    st.subheader("📋 Sesiones guardadas")
    mems_ses     = nexo.listar_memorias()
    sesiones_tab = [m for m in mems_ses if "historial" in m.get("tags", [])]

    if not sesiones_tab:
        st.info("Sin sesiones. Usa '💾 Guardar sesión' en el sidebar.")
    else:
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Total sesiones", len(sesiones_tab))
        col_s2.metric("Más reciente", sesiones_tab[0]["ts"] if sesiones_tab else "—")
        col_s3.metric("Disco total", f"{sum(s['kb'] for s in sesiones_tab):.1f} KB")

        st.divider()
        sel_ses = st.selectbox(
            "Sesión a revisar:",
            [s["id"] for s in sesiones_tab],
            format_func=lambda x: x.replace("sesion_", "Sesión ")
        )
        if sel_ses:
            path_ses = os.path.join(nexo.db_path, f"{sel_ses}.md")
            if os.path.exists(path_ses):
                with open(path_ses, "r", encoding="utf-8") as f:
                    res_text = f.read()
                campos = {
                    "TEMAS": "🏷️ Temas", "DECISIONES": "✅ Decisiones",
                    "PENDIENTE": "⏳ Pendiente", "USUARIO_INFO": "👤 Info detectada",
                    "SINOPSIS": "📝 Sinopsis"
                }
                for clave, titulo in campos.items():
                    for linea in res_text.split("\n"):
                        if linea.startswith(f"{clave}:"):
                            valor = linea.replace(f"{clave}:", "").strip()
                            if valor:
                                st.markdown(f"**{titulo}**")
                                st.info(valor)
                            break
                with st.expander("Ver texto completo"):
                    st.code(res_text, language="markdown")
