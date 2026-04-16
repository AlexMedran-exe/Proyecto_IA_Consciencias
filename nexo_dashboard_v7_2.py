"""
NEXO DE CONSCIENCIA v7.2 - Dashboard Elite Edition
Arranque: py -3.11 -m streamlit run nexo_dashboard_v7_2.py
"""

import os
import base64
import tempfile
import streamlit as st
import psutil
import requests
from nexo_consciencia_v7_2 import NexoCompleto, CONFIG, WHISPER_OK

try:
    import fitz
    PYMUPDF_OK = True
except ImportError:
    PYMUPDF_OK = False

try:
    from streamlit_mic_recorder import mic_recorder
    MIC_OK = True
except ImportError:
    MIC_OK = False

st.set_page_config(
    page_title="NEXO v7.2 | Elite Edition",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Area principal: solo chat y documentos */
    .main .block-container { padding-top: 1rem; max-width: 100%; }
    .stChatMessage p { font-size: 0.95rem; line-height: 1.65; }

    /* Badges de modo */
    .badge-chat { display:inline-block; padding:3px 12px; border-radius:12px;
        font-size:0.8rem; font-weight:700;
        background:#1e3a5f; color:#60a5fa; border:1px solid #60a5fa; }
    .badge-nexo { display:inline-block; padding:3px 12px; border-radius:12px;
        font-size:0.8rem; font-weight:700;
        background:#3a1f5f; color:#c084fc; border:1px solid #c084fc; }
    .badge-doc  { display:inline-block; padding:3px 12px; border-radius:12px;
        font-size:0.8rem; font-weight:700;
        background:#3a2a10; color:#fb923c; border:1px solid #fb923c; }

    /* Segunda Opinion destacada */
    .segunda-opinion {
        background: #1a1a2e; border-left: 3px solid #c084fc;
        padding: 10px 14px; margin-top: 12px;
        border-radius: 0 6px 6px 0; font-size: 0.9rem;
    }

    /* Seccion title en sidebar */
    .section-title { font-size:0.7rem; font-weight:700; letter-spacing:0.1em;
        color:#6b7280; text-transform:uppercase; margin:12px 0 4px 0; }

    /* Chunk info en documentos */
    .chunk-info { background:#1a2a1a; border-left:3px solid #4ade80;
        padding:6px 10px; margin:4px 0; font-size:0.8rem;
        border-radius:0 4px 4px 0; }
</style>
""", unsafe_allow_html=True)


# ── INICIALIZACION ────────────────────────────────────────────────────────────

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
    if "secciones_abiertas" not in st.session_state:
        st.session_state.secciones_abiertas = {
            "chats": True, "pdfs": True, "imagenes": True, "otros": False
        }
    if "voz_transcripcion" not in st.session_state:
        st.session_state.voz_transcripcion = ""

init_state()
nexo: NexoCompleto = st.session_state.nexo


# ── HELPERS ───────────────────────────────────────────────────────────────────

def cambiar_modo(nuevo_modo: str):
    st.session_state.modo = nuevo_modo
    if nuevo_modo == "chat":
        nexo.historial_sesion = st.session_state.historial_chat
    else:
        nexo.historial_sesion = st.session_state.historial_nexo

def guardar_chat_como_diario(nombre_id: str, tags_extra: list = []) -> tuple:
    if not st.session_state.historial_chat:
        return "El chat esta vacio.", False
    try:
        nexo._validar_id(nombre_id)
    except ValueError as e:
        return str(e), False
    import datetime
    contenido = f"CHAT GUARDADO: {nombre_id}\nFecha: {datetime.datetime.now()}\n\n"
    for t in st.session_state.historial_chat:
        contenido += f"Usuario: {t['user']}\nNexo: {t['nexo']}\n---\n"
    return nexo.guardar_memoria(nombre_id, contenido, ["chat"] + tags_extra)

def construir_prompt_nexo_fusionado(pregunta: str, ids_seleccionados: set) -> str:
    perfil       = nexo.cargar_perfil()
    bloque_fusion = ""
    ids_cargados  = []
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
        historial_texto = "\n--- CONVERSACION ACTUAL ---\n"
        for t in st.session_state.historial_nexo[-6:]:
            historial_texto += f"Usuario: {t['user']}\nNexo: {t['nexo']}\n"

    return f"""Eres EL NEXO, orquestador de conocimiento de elite de {perfil.get('nombre', 'Alex')}.
Hardware: {perfil.get('hardware', 'Acer Nitro')}.

MODO NEXO FUSIONADO — {len(ids_cargados)} fuente(s) activa(s): {ids_cargados}
Usa el contexto fusionado con prioridad sobre tu entrenamiento general.
Responde con autoridad y precision. Para respuestas complejas, incluye [SEGUNDA OPINION].

{'--- CONTEXTO FUSIONADO ---' + bloque_fusion if bloque_fusion else '(Sin diarios: conocimiento general)'}

{historial_texto}

Usuario: {pregunta}
Nexo:""".strip()

def llamar_modo_nexo(pregunta: str) -> str:
    try:
        pregunta = nexo._validar_query(pregunta)
    except ValueError as e:
        return f"Error: {e}"
    nexo._rl["streamlit_nexo"] = 0
    prompt    = construir_prompt_nexo_fusionado(pregunta, st.session_state.diarios_seleccionados)
    respuesta = nexo._llamar_ollama(prompt)
    st.session_state.historial_nexo.append({"user": pregunta, "nexo": respuesta})
    return respuesta

def renderizar_respuesta(respuesta: str):
    """
    Renderiza la respuesta separando el bloque [SEGUNDA OPINION]
    para darle formato visual destacado.
    """
    if "[SEGUNDA OPINION]" in respuesta:
        partes = respuesta.split("[SEGUNDA OPINION]", 1)
        st.markdown(partes[0])
        st.markdown(
            f'<div class="segunda-opinion"><strong>Segunda Opinion</strong><br>{partes[1].strip()}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(respuesta)

def extraer_texto_pdf(archivo_bytes: bytes) -> tuple:
    if not PYMUPDF_OK:
        return "", 0, 0
    try:
        doc = fitz.open(stream=archivo_bytes, filetype="pdf")
        paginas = []
        for num, pag in enumerate(doc, start=1):
            txt = pag.get_text("text")
            if txt.strip():
                paginas.append(f"[PAGINA {num}]\n{txt.strip()}")
        doc.close()
        texto_total = "\n\n".join(paginas)
        return texto_total, len(paginas), len(texto_total.split())
    except Exception as e:
        return f"Error extrayendo PDF: {e}", 0, 0

def chunkear_texto(texto: str, chunk_size: int = 1500, overlap: int = 200) -> list:
    palabras = texto.split()
    if len(palabras) <= chunk_size:
        return [texto]
    chunks, inicio = [], 0
    while inicio < len(palabras):
        fin = min(inicio + chunk_size, len(palabras))
        chunks.append(" ".join(palabras[inicio:fin]))
        if fin == len(palabras):
            break
        inicio = fin - overlap
    return chunks

def ingestar_pdf(archivo_bytes: bytes, nombre_base: str, tags_extra: list, chunk_size: int = 1500) -> dict:
    texto, num_pags, num_palabras = extraer_texto_pdf(archivo_bytes)
    if not texto or texto.startswith("Error"):
        return {"ok": False, "error": texto or "PDF vacio o sin texto seleccionable."}
    chunks = chunkear_texto(texto, chunk_size=chunk_size)
    tags   = ["pdf", "documento"] + tags_extra
    ids_guardados = []
    for i, chunk in enumerate(chunks, start=1):
        id_chunk  = f"{nombre_base}_p{str(i).zfill(2)}"
        cabecera  = f"DOCUMENTO PDF: {nombre_base}\nChunk {i} de {len(chunks)}\n\n"
        msg, ok   = nexo.guardar_memoria(id_chunk, cabecera + chunk, tags)
        if not ok:
            return {"ok": False, "error": f"Error en chunk {i}: {msg}"}
        ids_guardados.append(id_chunk)
    return {"ok": True, "paginas": num_pags, "palabras": num_palabras,
            "chunks": len(chunks), "ids": ids_guardados}

def describir_imagen(imagen_bytes: bytes, instruccion: str = "") -> str:
    imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")
    prompt = instruccion.strip() if instruccion.strip() else (
        "Describe esta imagen en detalle en espanol. "
        "Si contiene texto, transcribelo completo. "
        "Si es codigo, incluyelo integro. "
        "Si es un diagrama o captura, describe cada elemento visible."
    )
    return nexo._llamar_ollama_vision(prompt, imagen_b64)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — Configuracion, biblioteca y telemetria
#  El sidebar contiene TODO lo que no es chat ni documentos.
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    modo_actual = st.session_state.modo
    badge_map   = {
        "chat": '<div class="badge-chat">CHAT</div>',
        "nexo": '<div class="badge-nexo">NEXO</div>',
    }
    st.markdown(badge_map.get(modo_actual, ""), unsafe_allow_html=True)
    st.title("NEXO v7.2")

    # ── Seleccion de modo ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Modo</div>', unsafe_allow_html=True)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("Chat", use_container_width=True,
                     type="primary" if modo_actual == "chat" else "secondary"):
            cambiar_modo("chat"); st.rerun()
    with col_m2:
        if st.button("Nexo", use_container_width=True,
                     type="primary" if modo_actual == "nexo" else "secondary"):
            cambiar_modo("nexo"); st.rerun()

    if modo_actual == "chat":
        st.caption("Conversacion independiente. Sin contexto externo.")
    else:
        n_s = len(st.session_state.diarios_seleccionados)
        st.caption(f"Contexto fusionado. {n_s} diario(s) activo(s).")

    st.divider()

    # ── Biblioteca con secciones colapsables ─────────────────────────────────
    st.markdown('<div class="section-title">Biblioteca</div>', unsafe_allow_html=True)
    mems    = nexo.listar_memorias()
    diarios = [m for m in mems if "historial" not in m.get("tags", [])]

    if not diarios:
        st.caption("Sin diarios. Guarda un chat o sube un PDF.")
    else:
        grupos = {
            "chats":    {"icono": "Chat",     "items": []},
            "pdfs":     {"icono": "PDF",      "items": []},
            "imagenes": {"icono": "Imagen",   "items": []},
            "otros":    {"icono": "Otro",     "items": []},
        }
        for d in diarios:
            tags = d.get("tags", [])
            if   "chat"   in tags: grupos["chats"]["items"].append(d)
            elif "pdf"    in tags: grupos["pdfs"]["items"].append(d)
            elif "imagen" in tags: grupos["imagenes"]["items"].append(d)
            else:                  grupos["otros"]["items"].append(d)

        for gid, grupo in grupos.items():
            items = grupo["items"]
            if not items:
                continue

            abierto      = st.session_state.secciones_abiertas.get(gid, True)
            n_sel_grupo  = sum(1 for d in items if d["id"] in st.session_state.diarios_seleccionados)
            flecha       = "v" if abierto else ">"
            label_hdr    = f"{flecha} {grupo['icono']} ({len(items)})"
            if n_sel_grupo > 0:
                label_hdr += f" [{n_sel_grupo}]"

            col_hdr, col_all = st.sidebar.columns([0.75, 0.25])
            with col_hdr:
                if st.button(label_hdr, key=f"hdr_{gid}", use_container_width=True):
                    st.session_state.secciones_abiertas[gid] = not abierto
                    st.rerun()
            with col_all:
                todos = all(d["id"] in st.session_state.diarios_seleccionados for d in items)
                if st.button("All" if not todos else "X", key=f"all_{gid}",
                             use_container_width=True):
                    for d in items:
                        if todos:
                            st.session_state.diarios_seleccionados.discard(d["id"])
                        else:
                            st.session_state.diarios_seleccionados.add(d["id"])
                    st.rerun()

            if abierto:
                for d in items:
                    esta_sel = d["id"] in st.session_state.diarios_seleccionados
                    col_ck, col_inf = st.columns([0.15, 0.85])
                    with col_ck:
                        nv = st.checkbox("", value=esta_sel, key=f"ck_{d['id']}")
                        if nv != esta_sel:
                            if nv: st.session_state.diarios_seleccionados.add(d["id"])
                            else:  st.session_state.diarios_seleccionados.discard(d["id"])
                            st.rerun()
                    with col_inf:
                        label_btn = d["id"] if len(d["id"]) <= 18 else d["id"][:16] + "..."
                        if st.button(label_btn, key=f"btn_{d['id']}",
                                     use_container_width=True, help=d["id"]):
                            st.session_state.diario_inspeccionado = (
                                None if st.session_state.diario_inspeccionado == d["id"]
                                else d["id"]
                            )
                            st.rerun()
            st.markdown("&nbsp;", unsafe_allow_html=True)

    if st.session_state.diario_inspeccionado:
        did  = st.session_state.diario_inspeccionado
        path = os.path.join(nexo.db_path, f"{did}.md")
        st.markdown(f"**Preview: {did}**")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                prev = f.read()
            st.text_area("", prev[:500] + ("..." if len(prev) > 500 else ""),
                         height=120, disabled=True, label_visibility="collapsed")
        if st.button("Cerrar preview", use_container_width=True):
            st.session_state.diario_inspeccionado = None; st.rerun()

    st.divider()

    # ── Telemetria de hardware (solo en sidebar) ──────────────────────────────
    st.markdown('<div class="section-title">Hardware</div>', unsafe_allow_html=True)
    hw = nexo.get_hw_detalle()
    if hw:
        st.progress(hw.get("cpu_pct", 0) / 100,
                    text=f"CPU {hw.get('cpu_pct', 0):.0f}%")
        st.progress(hw.get("ram_pct", 0) / 100,
                    text=f"RAM {hw.get('ram_pct', 0):.0f}% "
                         f"({hw.get('ram_used_gb', 0):.1f}/{hw.get('ram_total_gb', 0):.1f}GB)")
        if hw.get("bat_pct") is not None:
            icono = "AC" if hw.get("bat_cargando") else "Bat"
            st.progress(hw["bat_pct"] / 100, text=f"{icono} {hw['bat_pct']:.0f}%")
        else:
            st.caption("AC / Sin bateria")
        st.caption(f"Disco libre: {hw.get('disco_libre_gb', 0):.1f}GB")
    else:
        st.caption("Telemetria N/A")

    st.divider()

    # ── Configuracion del modelo ──────────────────────────────────────────────
    st.markdown('<div class="section-title">Configuracion</div>', unsafe_allow_html=True)
    modelo_display = CONFIG["MODELO_PRINCIPAL"]
    st.caption(f"Modelo chat: {modelo_display}")
    st.caption(f"Modelo vision: {CONFIG['MODELO_VISION']}")
    st.caption(f"Whisper: {'base (listo)' if WHISPER_OK else 'no instalado'}")

    st.divider()

    # ── Acciones de sesion ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Sesion</div>', unsafe_allow_html=True)
    perfil = nexo.cargar_perfil()
    st.caption(f"Usuario: {perfil.get('nombre', 'Alex')} | Sesiones: {perfil.get('total_sesiones', 0)}")

    if st.button("Limpiar pantalla", use_container_width=True):
        if modo_actual == "chat":
            st.session_state.historial_chat = []
            nexo.historial_sesion = []
        else:
            st.session_state.historial_nexo = []
        st.rerun()

    if st.button("Guardar sesion", use_container_width=True, type="primary"):
        nexo.historial_sesion = (
            st.session_state.historial_chat if modo_actual == "chat"
            else st.session_state.historial_nexo
        )
        if nexo.historial_sesion:
            with st.spinner("Generando resumen..."):
                nexo.cerrar_sesion()
            st.success("Sesion guardada.")
            if modo_actual == "chat": st.session_state.historial_chat = []
            else:                     st.session_state.historial_nexo = []
            nexo.historial_sesion = []
            st.rerun()
        else:
            st.warning("Sesion vacia.")


# ══════════════════════════════════════════════════════════════════════════════
#  AREA PRINCIPAL — Solo chat y documentos
# ══════════════════════════════════════════════════════════════════════════════

tab_chat, tab_nexo, tab_docs, tab_diarios, tab_sesiones = st.tabs([
    "Chat",
    "Nexo",
    "Documentos",
    "Diarios",
    "Sesiones"
])


# ── TAB 1: CHAT ───────────────────────────────────────────────────────────────

with tab_chat:
    st.title("Chat Independiente")
    st.caption("Conversacion sin contexto externo. Guarda el chat al terminar para convertirlo en diario.")

    nexo.historial_sesion = st.session_state.historial_chat

    # ── Sistema de voz ──────────────────────────────────────────────────────
    if WHISPER_OK or MIC_OK:
        with st.expander("Dictado de voz", expanded=False):
            if not WHISPER_OK:
                st.warning("Instala openai-whisper: py -3.11 -m pip install openai-whisper")
            elif not MIC_OK:
                st.info(
                    "Para microfono en el dashboard instala: "
                    "py -3.11 -m pip install streamlit-mic-recorder\n\n"
                    "Alternativa: graba un audio y subelo como archivo WAV/MP3."
                )
                audio_file = st.file_uploader("Sube un audio (WAV/MP3)", type=["wav", "mp3"])
                if audio_file and st.button("Transcribir audio"):
                    with tempfile.NamedTemporaryFile(suffix=f".{audio_file.name.split('.')[-1]}",
                                                     delete=False) as tmp:
                        tmp.write(audio_file.getvalue())
                        tmp_path = tmp.name
                    with st.spinner("Transcribiendo con Whisper base..."):
                        texto, ok = nexo.transcribir_audio(tmp_path)
                    os.unlink(tmp_path)
                    if ok:
                        st.session_state.voz_transcripcion = texto
                        st.success(f"Transcripcion: {texto}")
                    else:
                        st.error(texto)
            else:
                # streamlit-mic-recorder disponible
                st.caption("Habla y el texto aparecera en el chat automaticamente.")
                audio_data = mic_recorder(
                    start_prompt="Grabar",
                    stop_prompt="Detener",
                    key="mic_chat"
                )
                if audio_data and audio_data.get("bytes"):
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp.write(audio_data["bytes"])
                        tmp_path = tmp.name
                    with st.spinner("Transcribiendo..."):
                        texto, ok = nexo.transcribir_audio(tmp_path)
                    os.unlink(tmp_path)
                    if ok:
                        st.session_state.voz_transcripcion = texto
                        st.success(f"Transcripcion: {texto}")
                    else:
                        st.error(texto)

    if not st.session_state.historial_chat:
        st.info("Chat vacio. Escribe o usa el dictado de voz para empezar.")

    for turno in st.session_state.historial_chat:
        with st.chat_message("user"):
            st.markdown(turno["user"])
        with st.chat_message("assistant"):
            renderizar_respuesta(turno["nexo"])

    # Input: texto normal o transcripcion de voz
    valor_inicial = st.session_state.voz_transcripcion
    if valor_inicial:
        st.session_state.voz_transcripcion = ""

    if prompt_chat := st.chat_input("Escribe tu mensaje...", key="input_chat"):
        with st.chat_message("user"):
            st.markdown(prompt_chat)
        with st.chat_message("assistant"):
            with st.spinner("El Nexo esta procesando..."):
                nexo._rl["streamlit"] = 0
                respuesta = nexo.despertar_nexo(prompt_chat, cliente="streamlit")
            renderizar_respuesta(respuesta)
        st.session_state.historial_chat = nexo.historial_sesion.copy()
        st.rerun()

    # Guardar como diario
    if st.session_state.historial_chat:
        st.divider()
        st.subheader("Guardar como diario")
        col_id, col_tags, col_btn = st.columns([2, 2, 1])
        with col_id:
            nombre_d = st.text_input("Nombre", placeholder="java_tareas", key="nomb_chat")
        with col_tags:
            tags_d = st.text_input("Tags", placeholder="java, universidad", key="tags_chat")
        with col_btn:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            if st.button("Guardar", type="primary", use_container_width=True):
                if nombre_d:
                    tags_l    = [t.strip() for t in tags_d.split(",") if t.strip()]
                    msg, ok   = guardar_chat_como_diario(nombre_d, tags_l)
                    if ok:
                        st.success(f"{msg} — Disponible en la Biblioteca.")
                        st.session_state.historial_chat = []
                        nexo.historial_sesion = []
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Escribe un nombre.")


# ── TAB 2: NEXO ───────────────────────────────────────────────────────────────

with tab_nexo:
    st.title("Modo Nexo")
    n_sel = len(st.session_state.diarios_seleccionados)
    if n_sel > 0:
        st.success(f"Contexto activo: {', '.join(sorted(st.session_state.diarios_seleccionados))}")
    else:
        st.warning("Sin diarios seleccionados. Marca uno o mas en la Biblioteca (sidebar).")

    if not st.session_state.historial_nexo:
        st.info("Selecciona diarios en el sidebar y empieza a hablar.")

    for turno in st.session_state.historial_nexo:
        with st.chat_message("user"):
            st.markdown(turno["user"])
        with st.chat_message("assistant"):
            renderizar_respuesta(turno["nexo"])

    if prompt_nexo := st.chat_input("Habla con el Nexo...", key="input_nexo"):
        with st.chat_message("user"):
            st.markdown(prompt_nexo)
        with st.chat_message("assistant"):
            with st.spinner(f"Consultando {n_sel} diario(s)..."):
                respuesta_nexo = llamar_modo_nexo(prompt_nexo)
            renderizar_respuesta(respuesta_nexo)
        st.rerun()


# ── TAB 3: DOCUMENTOS ─────────────────────────────────────────────────────────

with tab_docs:
    st.title("Ingestar Documentos")
    st.caption(
        "Convierte PDFs e imagenes en diarios. "
        "Una vez procesados aparecen en la Biblioteca disponibles para el Modo Nexo."
    )

    sub_pdf, sub_img = st.tabs(["PDF", "Imagen / Captura"])

    with sub_pdf:
        if not PYMUPDF_OK:
            st.error("pymupdf no instalado: py -3.11 -m pip install pymupdf")
        else:
            st.subheader("Subir PDF")
            st.caption("PDFs con texto seleccionable: apuntes, documentacion, papers.")
            col_up, col_cfg = st.columns([1, 1])
            with col_up:
                archivo_pdf = st.file_uploader("Selecciona un PDF", type=["pdf"])
                if archivo_pdf:
                    st.success(f"{archivo_pdf.name} ({archivo_pdf.size // 1000}KB)")
            with col_cfg:
                nombre_pdf = st.text_input("Nombre base", placeholder="apuntes_java")
                tags_pdf   = st.text_input("Tags", placeholder="universidad, java")
                chunk_size = st.slider("Chunk (palabras)", 500, 3000, 1500, 250)

            if archivo_pdf and nombre_pdf:
                if st.button("Procesar PDF", type="primary", use_container_width=True):
                    with st.spinner("Extrayendo texto..."):
                        resultado = ingestar_pdf(
                            archivo_pdf.getvalue(),
                            nombre_pdf,
                            [t.strip() for t in tags_pdf.split(",") if t.strip()],
                            chunk_size
                        )
                    if resultado["ok"]:
                        st.success(
                            f"PDF procesado: {resultado['paginas']} paginas, "
                            f"{resultado['palabras']:,} palabras, "
                            f"{resultado['chunks']} chunks."
                        )
                        for id_c in resultado["ids"]:
                            st.markdown(
                                f'<div class="chunk-info">{id_c}</div>',
                                unsafe_allow_html=True
                            )
                        st.rerun()
                    else:
                        st.error(resultado["error"])
            elif archivo_pdf:
                st.warning("Escribe un nombre para el diario.")

    with sub_img:
        st.subheader("Subir imagen o captura")
        st.caption("Llama 3.2 Vision analiza la imagen y guarda una descripcion textual como diario.")
        st.info("Requiere: ollama pull llama3.2-vision (~7GB)")

        col_img_up, col_img_cfg = st.columns([1, 1])
        with col_img_up:
            archivo_img = st.file_uploader("Selecciona imagen",
                                            type=["png", "jpg", "jpeg", "webp"])
            if archivo_img:
                st.image(archivo_img, caption=archivo_img.name, use_column_width=True)
        with col_img_cfg:
            nombre_img     = st.text_input("Nombre del diario", placeholder="error_java_npe",
                                           key="nombre_img")
            tags_img       = st.text_input("Tags", placeholder="error, java", key="tags_img")
            instruccion_img = st.text_area(
                "Instruccion (opcional)",
                placeholder="Que error muestra esta captura? / Describe el diagrama...",
                height=80
            )

        if archivo_img and nombre_img:
            if st.button("Analizar con IA", type="primary", use_container_width=True):
                with st.spinner("Analizando imagen con llama3.2-vision... (20-60s)"):
                    descripcion = describir_imagen(archivo_img.getvalue(), instruccion_img)

                if descripcion.startswith("Error") or "no instalado" in descripcion:
                    st.error(descripcion)
                else:
                    st.markdown("**Descripcion generada:**")
                    st.text_area("", descripcion, height=200,
                                 disabled=True, label_visibility="collapsed")
                    contenido_img = (
                        f"IMAGEN: {nombre_img}\n"
                        f"Archivo: {archivo_img.name}\n\n"
                        f"DESCRIPCION:\n{descripcion}"
                    )
                    tags_img_lista = [t.strip() for t in tags_img.split(",") if t.strip()]
                    msg, ok = nexo.guardar_memoria(nombre_img, contenido_img,
                                                   ["imagen"] + tags_img_lista)
                    if ok:
                        st.success(f"{msg} — Disponible en la Biblioteca.")
                        st.rerun()
                    else:
                        st.error(msg)
        elif archivo_img:
            st.warning("Escribe un nombre para el diario.")


# ── TAB 4: DIARIOS ────────────────────────────────────────────────────────────

with tab_diarios:
    st.subheader("Gestion de Diarios")
    with st.expander("Crear diario manual", expanded=False):
        col_da, col_db = st.columns(2)
        with col_da:
            new_id_m   = st.text_input("ID", placeholder="conocimientos_java")
            new_tags_m = st.text_input("Tags", placeholder="java, teoria")
        with col_db:
            new_content_m = st.text_area("Contenido", height=120)
        if st.button("Guardar diario manual", type="primary"):
            if new_id_m and new_content_m:
                tags_m    = [t.strip() for t in new_tags_m.split(",") if t.strip()]
                msg, ok   = nexo.guardar_memoria(new_id_m, new_content_m, tags_m)
                if ok: st.success(msg); st.rerun()
                else:  st.error(msg)
            else:
                st.warning("ID y contenido obligatorios.")

    st.divider()
    mems_tab    = nexo.listar_memorias()
    diarios_tab = [m for m in mems_tab if "historial" not in m.get("tags", [])]

    if not diarios_tab:
        st.info("No hay diarios. Guarda un chat, sube un PDF o una imagen.")
    else:
        pdfs_tab  = [d for d in diarios_tab if "pdf"    in d.get("tags", [])]
        imgs_tab  = [d for d in diarios_tab if "imagen" in d.get("tags", [])]
        chats_tab = [d for d in diarios_tab if "chat"   in d.get("tags", [])]
        otros_tab = [d for d in diarios_tab
                     if not any(t in d.get("tags", []) for t in ["pdf", "imagen", "chat"])]

        def mostrar_grupo_diario(titulo, items, icono):
            if not items: return
            st.markdown(f"**{icono} {titulo} ({len(items)})**")
            for d in items:
                m = "[x]" if d["id"] in st.session_state.diarios_seleccionados else "[ ]"
                st.markdown(
                    f"`{m}` **{d['id']}** · {d['ts']} · {d['kb']}KB · "
                    f"`{', '.join(d['tags'])}`"
                )

        mostrar_grupo_diario("PDFs", pdfs_tab, "PDF")
        mostrar_grupo_diario("Imagenes", imgs_tab, "IMG")
        mostrar_grupo_diario("Chats", chats_tab, "Chat")
        mostrar_grupo_diario("Otros", otros_tab, "Doc")

        st.divider()
        ids_todos = [d["id"] for d in diarios_tab]
        sel_d = st.selectbox("Ver contenido completo:", ["-- selecciona --"] + ids_todos)
        if sel_d != "-- selecciona --":
            path_c = os.path.join(nexo.db_path, f"{sel_d}.md")
            if os.path.exists(path_c):
                with open(path_c, "r", encoding="utf-8") as f:
                    cont_c = f.read()
                st.text_area("", cont_c, height=350,
                             disabled=True, label_visibility="collapsed")
                st.caption(f"{len(cont_c)} chars · {len(cont_c.encode('utf-8'))} bytes")


# ── TAB 5: SESIONES ───────────────────────────────────────────────────────────

with tab_sesiones:
    st.subheader("Sesiones guardadas")
    mems_ses  = nexo.listar_memorias()
    ses_tab   = [m for m in mems_ses if "historial" in m.get("tags", [])]

    if not ses_tab:
        st.info("Sin sesiones. Usa 'Guardar sesion' en el sidebar.")
    else:
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("Total", len(ses_tab))
        col_s2.metric("Mas reciente", ses_tab[0]["ts"] if ses_tab else "--")
        col_s3.metric("Disco", f"{sum(s['kb'] for s in ses_tab):.1f} KB")

        st.divider()
        sel_ses = st.selectbox(
            "Sesion a revisar:",
            [s["id"] for s in ses_tab],
            format_func=lambda x: x.replace("sesion_", "Sesion ")
        )
        if sel_ses:
            path_ses = os.path.join(nexo.db_path, f"{sel_ses}.md")
            if os.path.exists(path_ses):
                with open(path_ses, "r", encoding="utf-8") as f:
                    res_text = f.read()
                campos = {
                    "TEMAS": "Temas", "DECISIONES": "Decisiones",
                    "PENDIENTE": "Pendiente", "USUARIO_INFO": "Info detectada",
                    "SINOPSIS": "Sinopsis"
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