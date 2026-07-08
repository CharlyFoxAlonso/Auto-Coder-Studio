"""
app.py - Agente Programador v4.1 (DeepSeek Coder)
Interfaz de chat con ejecución automática de herramientas.

Cambios vs v4.0:
 - Validación de rutas unificada en core/security.py (se quitó la validación
   manual y débil de ".." / "/" que no cubría Windows).
 - Persistencia correcta del historial en TODAS las ramas del loop.
 - Modelo unificado: se lee una sola vez de coder_agent.MODELO_CODER.
 - Loop con confirmación del usuario antes de cada write_file.
"""
import streamlit as st
import os
import json
from dotenv import load_dotenv
from core.coder_agent import preguntar_coder, forzar_json, MODELO_CODER, obtener_modelos_disponibles
from core.file_manager import leer_archivo, escribir_archivo, listar_archivos
from core.drawers_manager import cargar_cajones, guardar_cajones, agregar_subcajon
from core.cloud_processor import process_document_cloud
from core.rag_manager import indexar_chunks, buscar_conocimiento

load_dotenv()

st.set_page_config(
    page_title="👨‍💻 Agente Programador",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estado de sesión
if "historial_chat" not in st.session_state:
    st.session_state.historial_chat = []
if "modelo_seleccionado" not in st.session_state:
    st.session_state.modelo_seleccionado = MODELO_CODER
if "carpeta_trabajo" not in st.session_state:
    st.session_state.carpeta_trabajo = ""
# Mensaje pendiente del usuario, para continuar el loop entre ejecuciones.
if "prompt_pendiente" not in st.session_state:
    st.session_state.prompt_pendiente = None
# Escritura pendiente de confirmación: {"ruta":..., "contenido":...}
if "escritura_pendiente" not in st.session_state:
    st.session_state.escritura_pendiente = None
# Archivos creados confirmados durante la tarea actual.
if "archivos_creados" not in st.session_state:
    st.session_state.archivos_creados = []
# Estados de control del loop ReAct.
if "loop_activo" not in st.session_state:
    st.session_state.loop_activo = False
if "iteracion" not in st.session_state:
    st.session_state.iteracion = 0
if "ultimo_archivo_creado" not in st.session_state:
    st.session_state.ultimo_archivo_creado = None
if "contador_repeticiones" not in st.session_state:
    st.session_state.contador_repeticiones = 0
if "resultado_final" not in st.session_state:
    st.session_state.resultado_final = None
# TERMINADO: que vino mezclado con un write_file en la misma respuesta.
# Se aplica recién tras confirmar/descartar la escritura pendiente.
if "terminado_pendiente" not in st.session_state:
    st.session_state.terminado_pendiente = None

MAX_ITER = 20

# Sidebar
with st.sidebar:
    st.title("⚙️ Configuración")
    
    st.session_state.modelo_seleccionado = st.selectbox(
        "🧠 Modelo:",
        options=[MODELO_CODER],
        index=0,
        help="Usando Qwen 2.5 Coder 14B para máxima potencia local"
    )

    st.session_state.carpeta_trabajo = st.text_input(
        "📁 Carpeta de trabajo:",
        value=st.session_state.carpeta_trabajo,
        help="Archivos se crearán DENTRO de esta carpeta"
    )

    st.divider()

    st.write("**🛠️ Herramientas:**")
    if st.button("📋 Listar archivos", use_container_width=True):
        if st.session_state.carpeta_trabajo and os.path.exists(st.session_state.carpeta_trabajo):
            estructura, error = listar_archivos(st.session_state.carpeta_trabajo)
            if error:
                st.error(error)
            else:
                with st.expander("Ver estructura"):
                    st.code(estructura)
        else:
            st.warning("Configurá una carpeta válida primero")

    # Adjuntar archivos manualmente al contexto del próximo prompt.
    if "adjuntar_archivos" not in st.session_state:
        st.session_state.adjuntar_archivos = []
    if st.session_state.carpeta_trabajo and os.path.exists(st.session_state.carpeta_trabajo):
        _, _, nombres_archivos = next(os.walk(st.session_state.carpeta_trabajo), (None, None, []))
        if nombres_archivos:
            st.multiselect(
                "📎 Adjuntar al contexto",
                options=sorted(nombres_archivos),
                key="adjuntar_archivos",
                help="Marcá los archivos que ya existen y querés que el agente vea antes de modificar."
            )

    if st.button("🗑️ Limpiar historial", use_container_width=True):
        st.session_state.historial_chat = []
        st.session_state.loop_activo = False
        st.session_state.prompt_pendiente = None
        st.session_state.escritura_pendiente = None
        st.session_state.archivos_creados = []
        st.session_state.iteracion = 0
        st.session_state.ultimo_archivo_creado = None
        st.session_state.contador_repeticiones = 0
        st.session_state.resultado_final = None
        st.session_state.terminado_pendiente = None
        st.rerun()

    if st.session_state.loop_activo:
        if st.button("🛑 Detener Agente", type="primary", use_container_width=True):
            st.session_state.loop_activo = False
            st.session_state.prompt_pendiente = None
            st.success("Agente detenido por el usuario.")
            st.rerun()

    st.divider()

    # --- SECCIÓN DE GESTIÓN DE CONOCIMIENTO (RAG) ---
    st.subheader("🧠 Gestión de Conocimiento")
    
    # Cargar jerarquía actual
    cajones_data = cargar_cajones()
    lista_cajones = list(cajones_data.keys())
    
    # 1. Selección de Cajón
    cajon_sel = st.selectbox("📁 Cajón Principal:", options=lista_cajones)
    
    # 2. Selección de Sub-Cajón
    subcajones = list(cajones_data.get(cajon_sel, {}).keys())
    subcajon_sel = st.selectbox("📁 Sub-Cajón:", options=subcajones) if subcajones else "Ninguno"
    
    # 3. Botón Crear Sub-Cajón
    nuevo_sub = st.text_input("➕ Nuevo Sub-Cajón:", placeholder="Ej: FastAPI", key="new_sub_input")
    if st.button("Agregar Sub-Cajón", use_container_width=True):
        if nuevo_sub:
            agregar_subcajon(cajon_sel, nuevo_sub)
            st.success(f"Sub-cajón '{nuevo_sub}' creado!")
            st.rerun()
        else:
            st.warning("Escribí un nombre para el sub-cajón")

    st.divider()
    
    # 4. Carga de Documentos
    uploaded_file = st.file_uploader(
        "📄 Subir Documento para Digestor", 
        type=["pdf", "docx", "txt"],
        help="Gemma 4 procesará este archivo y lo indexará en el sub-cajón seleccionado."
    )

    if uploaded_file and subcajon_sel != "Ninguno":
        if st.button("🚀 Procesar e Indexar", type="primary", use_container_width=True):
            import time
            start_time = time.time()
            
            with st.status("☁️ Conectando con Gemma 4 Cloud...", expanded=True) as status:
                st.write("📄 Extrayendo texto del documento...")
                # Ejecutar el proceso real
                chunks, error = process_document_cloud(uploaded_file, cajon_sel, subcajon_sel)
                
                if error:
                    st.error(f"❌ Error: {error}")
                    status.update(label="Error en el procesamiento", state="error")
                else:
                    st.write(f"🧠 Digestión completa. Se generaron {len(chunks)} fragmentos.")
                    st.write("💾 Indexando en la base de datos local...")
                    
                    # INDEXACIÓN REAL AQUÍ
                    ok_index = indexar_chunks(chunks, cajon_sel, subcajon_sel)
                    
                    if ok_index:
                        status.update(label="✅ Documento procesado e indexado", state="complete")
                    else:
                        status.update(label="❌ Error al indexar localmente", state="error")
            
            end_time = time.time()
            st.info(f"⏱️ Tiempo total: {end_time - start_time:.2f} segundos")
    elif uploaded_file and subcajon_sel == "Ninguno":
        st.warning("Seleccioná un Sub-Cajón antes de procesar.")

    st.divider()

    st.divider()
    st.info(
        f"**Modelo:** {st.session_state.modelo_seleccionado}\n\n"
        f"**Timeout:** 5 min por iteración\n\n"
        f"**Máx iteraciones:** {MAX_ITER}\n\n"
        f"**Confirmación:** cada write_file requiere tu OK."
    )

# Título principal
st.title("👨‍💻 Agente Programador Autónomo")
st.markdown(f"""
<div style='background-color: #1e1e1e; padding: 10px; border-radius: 5px; margin-bottom: 20px;'>
    📁 <b>Carpeta activa:</b> <code style='color: #00ff00;'>{st.session_state.carpeta_trabajo or '⚠️ No configurada'}</code>
</div>
""", unsafe_allow_html=True)

# Ejemplos de uso
with st.expander("💡 Ejemplos de qué pedir"):
    st.markdown("""
    - "Creá un programa que calcule la tabla de multiplicar"
    - "Hacé una calculadora con menú interactivo"
    - "Creá un script que organice archivos por extensión"
    - "Programá un juego de adivinar números"
    - "Creá un sistema de gestión de contactos (múltiples archivos)"
    """)


# ---------------------------------------------------------------------------
# Render del historial
# ---------------------------------------------------------------------------
def render_historial():
    for msg in st.session_state.historial_chat:
        # Cambiamos "tool" por un emoji para evitar que Streamlit ponga la letra "T"
        role = msg["role"]
        avatar = "🤖" if role == "assistant" else "👤" if role == "user" else "🛠️"
        
        with st.chat_message(avatar):
            contenido = msg.get("content", "")
            if role == "tool":
                if len(contenido) > 1000:
                    with st.expander("Ver contenido completo"):
                        st.code(contenido, language="text")
                else:
                    st.code(contenido, language="text")
            elif role == "assistant":
                if "TERMINADO:" in contenido:
                    st.success(contenido)
                elif "[Usando" in contenido or "[Respuesta inválida" in contenido:
                    st.info(contenido)
                else:
                    st.markdown(contenido)
            else:
                st.markdown(contenido)


render_historial()


# ---------------------------------------------------------------------------
# Ejecución de herramientas
# ---------------------------------------------------------------------------
def ejecutar_herramienta(herramienta, argumentos, carpeta):
    """Ejecuta una herramienta y devuelve el resultado.

    write_file NO se ejecuta acá: queda como 'escritura_pendiente' para que
    el usuario confirme o descarte.
    """
    if herramienta == "list_files":
        estructura, error = listar_archivos(carpeta)
        return {"resultado": estructura, "error": error}

    elif herramienta == "read_file":
        ruta = argumentos.get("ruta", "")
        contenido, error = leer_archivo(carpeta, ruta)
        return {"resultado": contenido, "error": error, "ruta": ruta}

    elif herramienta == "write_file":
        ruta = argumentos.get("ruta", "")
        contenido = argumentos.get("contenido", "")
        if not ruta:
            return {"resultado": None, "error": "Falta el parámetro 'ruta'"}
        # La validación de path-traversal ya la hace escribir_archivo,
        # pero la chequeamos antes para no mostrar el panel de confirmación.
        from core.security import validar_ruta_segura
        ok, msg = validar_ruta_segura(carpeta, ruta)
        if not ok:
            return {"resultado": None, "error": msg}
        if not os.path.splitext(ruta)[1]:
            return {"resultado": None, "error": "La ruta debe tener extensión"}
        return {
            "resultado": "pendiente",
            "error": "",
            "ruta": ruta,
            "contenido": contenido,
        }

    elif herramienta == "delete_file":
        ruta = argumentos.get("ruta", "")
        from core.file_manager import borrar_archivo
        ok, msg = borrar_archivo(carpeta, ruta)
        if ok:
            return {"resultado": msg, "error": ""}
        else:
            return {"resultado": None, "error": msg}

    return {"resultado": None, "error": f"Herramienta desconocida: {herramienta}"}


# ---------------------------------------------------------------------------
# Un paso del loop ReAct. Devuelve 'continuar', 'listo' o 'esperar_usuario'.
# ---------------------------------------------------------------------------
def paso_loop(prompt_actual):
    """Ejecuta UNA iteración del loop ReAct por rerun de Streamlit.

    Returns:
        ("continuar", prompt_siguiente)   -> seguir iterando
        ("listo", msg_final)               -> tarea terminada
        ("esperar_usuario", None)          -> hay escritura pendiente
        ("pausar", None)                   -> no hay nada más que hacer
    """
    historial = st.session_state.historial_chat
    carpeta = st.session_state.carpeta_trabajo

    # Cap del historial para no contaminar el contexto (mantener los últimos
    # N mensajes y siempre conservar el primer mensaje "user" inicial).
    MAX_HIST = 12
    if len(historial) > MAX_HIST:
        primer_user = next((m for m in historial if m["role"] == "user"), None)
        st.session_state.historial_chat = (
            ([primer_user] if primer_user else [])
            + historial[-(MAX_HIST - 1):]
        )
        historial = st.session_state.historial_chat

    if st.session_state.iteracion >= MAX_ITER:
        return ("listo",
                f"⚠️ Límite de {MAX_ITER} iteraciones alcanzado. "
                f"Archivos creados: {st.session_state.archivos_creados}")

    # Inyección de contexto: si el usuario pide "agregar/completar/modificar"
    # algo en un archivo existente, lo leemos y lo adjuntamos al prompt para
    # que el modelo devuelva el archivo ENTERO (no solo el parche).
    prompt_inyectado = _preparar_prompt_con_contexto(
        prompt_actual, carpeta, st.session_state.archivos_creados
    )
    
    # REFUERZO DE MEMORIA: Si hay un archivo que se acaba de crear/modificar,
    # le recordamos al modelo su contenido exacto para evitar que reinicie la tarea.
    if st.session_state.ultimo_archivo_creado:
        u_ruta = st.session_state.ultimo_archivo_creado
        u_cont, _ = leer_archivo(carpeta, u_ruta)
        if u_cont:
            prompt_inyectado += f"\n\n[ESTADO ACTUAL DEL ARCHIVO {u_ruta}]:\n```\n{u_cont}\n```\n"
            prompt_inyectado += "Teniendo en cuenta este contenido, continuá con la siguiente acción."

    st.session_state.iteracion += 1
    with st.spinner(f"🔄 Iteración {st.session_state.iteracion}/{MAX_ITER}..."):
        respuesta = preguntar_coder(prompt_inyectado, historial, modelo_seleccionado=st.session_state.modelo_seleccionado)

    with st.expander(f"🔍 Ver respuesta del modelo (iteración {st.session_state.iteracion - 1})"):
        st.code(respuesta)

    # Primero extraemos el JSON si existe, para poder validar la terminación
    data = forzar_json(respuesta)

    # Si el modelo respondió "TERMINADO:" (solo eso, sin JSON previo), cerramos
    if respuesta.startswith("TERMINADO:") or respuesta.strip() == "TERMINADO":
        # VALIDACIÓN: Si el modelo intenta terminar pero no hubo una herramienta 
        # ejecutada en esta iteración, podría estar mintiendo (alucinación).
        if not data:
             # Si no hay data de herramienta en esta vuelta, el modelo solo dijo TERMINADO
             # sin ejecutar nada. Esto es aceptable si la tarea ya terminó.
             pass 
        return ("listo", respuesta)

    if not data:
        # El modelo no devolvió JSON ni TERMINADO.
        st.warning("⚠️ El modelo respondió con texto en lugar de JSON. "
                   "Reintentando con instrucción más estricta...")
        historial.append({"role": "assistant",
                          "content": "[Respuesta inválida - se esperaba JSON]"})
        prompt_mas_estricto = (
            "ERROR CRÍTICO: Debés responder EXCLUSIVAMENTE con JSON así:\n"
            '{"herramienta": "write_file", "argumentos": {"ruta": "archivo.py", '
            '"contenido": "codigo"}, "pensamiento": "razon"}\n\n'
            'O con "TERMINADO: " al final. NO hables, NO expliques. '
            "Solo JSON o TERMINADO."
        )
        return ("continuar", prompt_mas_estricto)

    herramienta = data.get("herramienta")
    argumentos = data.get("argumentos", {}) or {}
    pensamiento = data.get("pensamiento", "")

    if pensamiento:
        st.markdown(f"**Pensamiento:** {pensamiento}")

    # Detección de reescritura repetida (solo si el contenido es idéntico)
    if herramienta == "write_file":
        ruta_actual = argumentos.get("ruta", "")
        contenido_actual = argumentos.get("contenido", "")
        if ruta_actual == st.session_state.ultimo_archivo_creado and contenido_actual == st.session_state.get("ultimo_contenido_escrito"):
            st.session_state.contador_repeticiones += 1
            if st.session_state.contador_repeticiones >= 2:
                st.warning(f"⚠️ Reescritura idéntica de {ruta_actual}. Forzando terminación.")
                return (
                    "listo",
                    f"TERMINADO: Tarea completada (reescritura idéntica de "
                    f"{ruta_actual}). Archivos: "
                    f"{st.session_state.archivos_creados}"
                )
        else:
            st.session_state.contador_repeticiones = 0
            st.session_state.ultimo_archivo_creado = ruta_actual
            st.session_state.ultimo_contenido_escrito = contenido_actual

    resultado = ejecutar_herramienta(herramienta, argumentos, carpeta)
    historial.append({"role": "assistant", "content": f"[Usando {herramienta}]"})

    # CASO ESPECIAL: write_file queda pendiente de confirmación.
    if herramienta == "write_file" and resultado["resultado"] == "pendiente":
        st.session_state.escritura_pendiente = {
            "ruta": resultado["ruta"],
            "contenido": resultado["contenido"],
        }
        # Si el modelo también dijo TERMINADO: en la misma respuesta, lo
        # recordamos para cerrar el loop apenas el usuario confirme o
        # descarte este archivo (no antes, si no, no se guardaría nada).
        if "TERMINADO:" in respuesta:
            st.session_state.terminado_pendiente = respuesta
        return ("esperar_usuario", None)

    # Permanente
    if resultado["error"]:
        historial.append({"role": "tool",
                          "content": f"❌ Error: {resultado['error']}"})
        st.error(f"❌ Error en {herramienta}: {resultado['error']}")
        return ("continuar",
                f"Error: {resultado['error']}. Continuá con la tarea.")

    # Éxito de tools que no son write_file
    if herramienta == "read_file":
        ruta = argumentos.get("ruta", "")
        # Agregamos el contenido al historial para que el modelo lo "vea".
        contenido = resultado["resultado"] or ""
        if len(contenido) > 4000:
            contenido = contenido[:4000] + "\n... [truncado]"
        historial.append({"role": "tool",
                          "content": f"✅ Contenido de {ruta}:\n{contenido}"})
    elif herramienta == "list_files":
        historial.append({"role": "tool",
                          "content": f"✅ Archivos:\n{resultado['resultado']}"})
    elif herramienta == "buscar_conocimiento":
        # El agente busca en el RAG local
        cajon = argumentos.get("cajon")
        subcajon = argumentos.get("subcajon")
        query = argumentos.get("query", "")
        
        res_rag = buscar_conocimiento(query, cajon, subcajon)
        historial.append({"role": "tool",
                          "content": f"📚 Resultados de la biblioteca:\n{res_rag}"})


    return ("continuar",
            "Si ya creaste TODOS los archivos necesarios, respondé "
            "'TERMINADO: ' explicando cómo usarlo. Si falta algún archivo, "
            "crealo ahora.")


# ---------------------------------------------------------------------------
# Detección de "parte N de M" y archivos a adjuntar al contexto
# ---------------------------------------------------------------------------
import re as _re

# Palabras clave que sugieren "modificar un archivo existente" en vez de
# "crear uno nuevo desde cero".
_KEYWORDS_MODIFICAR = (
    "agregá", "agrega", "agregar",
    "completá", "completa", "completar",
    "modificá", "modifica", "modificar",
    "sumale", "sumá", "sumar",
    "parte 2 de", "parte 3 de", "parte 2/", "parte 3/",
    "ahora hacé", "ahora haz", "ahora hacé",
)

# Regex para captar cosas como "index.html", "carpeta/archivo.py", etc.
_RUTA_RE = _re.compile(
    r"([\w\-./\\]+\.(?:html|htm|css|js|py|json|md|txt))",
    _re.IGNORECASE,
)


def _detectar_archivos_en_prompt(prompt_texto):
    """Devuelve la lista de rutas candidatas mencionadas en el prompt."""
    return list({m.group(1).replace("\\", "/") for m in _RUTA_RE.finditer(prompt_texto)})


def _parsear_parte(prompt_texto):
    """Detecta si el prompt dice 'Parte N de M' o 'Punto N de M'."""
    m = _re.search(r"(?:parte|punto)\s*(\d+)\s*(?:de|/)\s*(\d+|\?)",
                   prompt_texto, _re.IGNORECASE)
    if m:
        actual = int(m.group(1))
        total = m.group(2)
        total = int(total) if total.isdigit() else None
        return actual, total
    return None, None


def _preparar_prompt_con_contexto(prompt_actual, carpeta, archivos_creados):
    """Si el prompt parece pedir modificación, adjunta el archivo existente.

    - Detecta keywords de modificación.
    - Detecta rutas mencionadas (ej: "index.html").
    - Detecta "Parte N de M" (inyecta nota).
    - Si el usuario marcó adjuntos manuales, también los agrega.
    """
    lower = prompt_actual.lower()
    quiere_modificar = any(kw in lower for kw in _KEYWORDS_MODIFICAR)

    rutas_a_adjuntar = []
    for r in _detectar_archivos_en_prompt(prompt_actual):
        rutas_a_adjuntar.append(r)
    for r in (st.session_state.get("adjuntar_archivos") or []):
        if r not in rutas_a_adjuntar:
            rutas_a_adjuntar.append(r)
    # Si hay archivos creados anteriormente y el prompt habla de "agregar /
    # Parte N de M / modificar", los adjuntamos TODOS para que el modelo
    # no rompa nada previo.
    if quiere_modificar:
        for r in archivos_creados or []:
            if r not in rutas_a_adjuntar:
                rutas_a_adjuntar.append(r)

    bloques = []
    actual_num, total_num = _parsear_parte(prompt_actual)
    if actual_num is not None:
        bloques.append(
            f"[CONTEXTO DEL USUARIO] Estás recibiendo la Parte {actual_num}"
            + (f" de {total_num}" if total_num else "")
            + ". Mantené TODA la parte anterior intacta y agregá solo lo nuevo."
        )

    for ruta in rutas_a_adjuntar:
        ok, contenido = leer_archivo(carpeta, ruta)
        if ok and contenido is not None:
            contenido_str = contenido if isinstance(contenido, str) else str(contenido)
            # Cap por archivo para no volar el contexto (4KB por archivo).
            if len(contenido_str) > 4000:
                contenido_str = contenido_str[:4000] + "\n... [truncado a 4KB]"
            bloques.append(
                f"[ARCHIVO EXISTENTE: {ruta}]\n```\n{contenido_str}\n```"
            )

    if not bloques:
        return prompt_actual

    bloques.append(
        "[INSTRUCCIÓN] Tu respuesta debe ser EXACTAMENTE un solo JSON así: "
        '{"herramienta": "write_file", "argumentos": {"ruta": "<misma ruta>", '
        '"contenido": "<archivo ENTERO ya modificado, incluyendo TODO lo previo + lo nuevo>"}, '
        '"pensamiento": "razón breve"}. Sin markdown, sin texto extra, sin explicación. '
        "Si ya está todo terminado, respondé SOLO: TERMINADO: [instrucciones]"
    )
    bloques.append(f"[PETICIÓN DEL USUARIO]\n{prompt_actual}")
    return "\n\n".join(bloques)


# ---------------------------------------------------------------------------
# Panel de confirmación de escritura
# ---------------------------------------------------------------------------
def render_panel_escritura_pendiente():
    pend = st.session_state.escritura_pendiente
    if not pend:
        return False  # no hay panel

    st.warning(f"📝 El agente quiere crear **{pend['ruta']}**. "
               f"Revisá el contenido antes de confirmar.")

    col1, col2, col3 = st.columns([1, 1, 4])
    confirmar = col1.button("✅ Confirmar", type="primary")
    descartar = col2.button("🗑️ Descartar")
    
    # Nueva casilla de instrucciones adicionales
    instrucciones = st.text_input("💬 Instrucción adicional o ajuste:", 
                                  placeholder="Ej: Cambia el nombre a X, o 'Suficiente, detené el loop'")
    
    with st.expander("Ver contenido propuesto", expanded=True):
        st.code(pend["contenido"], language="python")

    if confirmar:
        carpeta = st.session_state.carpeta_trabajo
        ok, res = escribir_archivo(carpeta, pend["ruta"], pend["contenido"])
        historial = st.session_state.historial_chat
        if ok:
            st.success(f"✅ Archivo creado: {pend['ruta']}")
            historial.append({"role": "tool",
                              "content": f"✅ Guardado: {pend['ruta']}"})
            if pend["ruta"] not in st.session_state.archivos_creados:
                st.session_state.archivos_creados.append(pend["ruta"])
            
            st.session_state.escritura_pendiente = None
            
            # Si el usuario escribió algo, lo sumamos al prompt siguiente
            if instrucciones:
                st.session_state.prompt_pendiente = f"El archivo fue guardado. {instrucciones}"
            elif st.session_state.terminado_pendiente:
                st.session_state.prompt_pendiente = None
            else:
                st.session_state.prompt_pendiente = (
                    f"Archivo confirmado y guardado: {pend['ruta']}. "
                    "Si ya creaste todos los archivos necesarios, respondé "
                    "EXACTAMENTE: TERMINADO: [instrucciones de uso]. "
                    "Si falta otro archivo, crealo ahora."
                )
        else:
            st.error(f"❌ Error al escribir: {res}")
            historial.append({"role": "tool",
                              "content": f"❌ Error escribiendo {pend['ruta']}: {res}"})
            st.session_state.prompt_pendiente = (
                f"Error al escribir {pend['ruta']}: {res}. "
                "Corregí y reintentá."
            )
            st.session_state.escritura_pendiente = None
        return True

    if descartar:
        historial = st.session_state.historial_chat
        historial.append(
            {"role": "tool",
             "content": f"⏸️ El usuario DESCARTÓ la creación de {pend['ruta']}."}
        )
        st.info(f"⏸️ Creación de {pend['ruta']} descartada.")
        st.session_state.escritura_pendiente = None
        
        # Si el usuario puso instrucciones al descartar, las usamos
        if instrucciones:
            st.session_state.prompt_pendiente = f"El usuario descartó el archivo. {instrucciones}"
        else:
            st.session_state.prompt_pendiente = (
                f"El usuario rechazó crear {pend['ruta']}. "
                "No insistas con ese archivo. Continuá con otra parte de la tarea "
                "o terminá con TERMINADO:."
            )
        return True

    return False  # No hubo interacción, el loop debe esperar al usuario


# ---------------------------------------------------------------------------
# Mostrar resultado final si terminó
# ---------------------------------------------------------------------------
if st.session_state.resultado_final:
    res = st.session_state.resultado_final
    if "TERMINADO:" in res:
        st.success("🎉 **Tarea completada!**")
        if st.session_state.archivos_creados:
            st.info(
                f"📁 **Archivos creados:** "
                f"{', '.join(st.session_state.archivos_creados)}\n\n"
                f"**Ubicación:** `{st.session_state.carpeta_trabajo}`"
            )
    elif "Límite" in res:
        st.warning(res)
    else:
        st.info(res)


# ---------------------------------------------------------------------------
# Driver del loop
# ---------------------------------------------------------------------------
def hay_escritura_pendiente():
    return st.session_state.escritura_pendiente is not None


# Si hay escritura pendiente, renderiza el panel y espera.
if hay_escritura_pendiente():
    confirmo_o_descarto = render_panel_escritura_pendiente()
    if confirmo_o_descarto and st.session_state.terminado_pendiente:
        # El modelo ya había dicho TERMINADO: junto con este write_file.
        # Ahora que el usuario decidió sobre el archivo, cerramos el loop.
        st.session_state.resultado_final = st.session_state.terminado_pendiente
        st.session_state.terminado_pendiente = None
        st.session_state.loop_activo = False
        st.session_state.iteracion = 0
        st.session_state.ultimo_archivo_creado = None
        st.session_state.contador_repeticiones = 0
        st.session_state.escritura_pendiente = None
        st.session_state.prompt_pendiente = None
        st.rerun()
    elif confirmo_o_descarto and st.session_state.prompt_pendiente:
        st.rerun()
    # Si todavía está decidido, no seguimos: dejamos panel visible.
else:
    # Loop normal
    if hay_escritura_pendiente():
        st.stop()

    # Si acabamos de confirmar/descartar un archivo, hay prompt pendiente.
    if st.session_state.prompt_pendiente and st.session_state.loop_activo:
        prompt_actual = st.session_state.prompt_pendiente
        st.session_state.prompt_pendiente = None
        estado, payload = paso_loop(prompt_actual)

        if estado == "listo":
            st.session_state.loop_activo = False
            st.session_state.resultado_final = payload
            st.session_state.iteracion = 0
            st.session_state.ultimo_archivo_creado = None
            st.session_state.contador_repeticiones = 0
        elif estado == "esperar_usuario":
            # había write_file: mostrar panel en el siguiente render
            st.rerun()
        elif estado == "continuar":
            st.session_state.prompt_pendiente = payload
            st.rerun()
        elif estado == "pausar":
            st.session_state.loop_activo = False


# ---------------------------------------------------------------------------
# Input del usuario
# ---------------------------------------------------------------------------
prompt = st.chat_input("¿Qué querés programar hoy?")
if prompt:
    if not st.session_state.carpeta_trabajo:
        st.error("⚠️ **Primero configurá una carpeta de trabajo en el sidebar**")
    elif not os.path.exists(st.session_state.carpeta_trabajo):
        st.error(f"❌ La carpeta no existe: `{st.session_state.carpeta_trabajo}`")
    else:
        st.session_state.historial_chat.append({"role": "user", "content": prompt})
        st.session_state.loop_activo = True
        st.session_state.iteracion = 0
        st.session_state.archivos_creados = []
        st.session_state.ultimo_archivo_creado = None
        st.session_state.contador_repeticiones = 0
        st.session_state.resultado_final = None
        st.session_state.prompt_pendiente = prompt
        st.rerun()
