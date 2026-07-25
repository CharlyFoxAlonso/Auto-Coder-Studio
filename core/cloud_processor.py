import os
import json
from google import genai
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
import io

load_dotenv()

# Configuración de la API de Google (Nueva librería google-genai)
MODEL_NAME = os.getenv("GOOGLE_DIGEST_MODEL", "gemini-2.5-flash")

def extract_text(uploaded_file):
    """Extrae texto de archivos PDF, DOCX y TXT."""
    file_ext = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_ext == 'pdf':
            reader = PdfReader(uploaded_file)
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return text
        elif file_ext == 'docx':
            doc = Document(io.BytesIO(uploaded_file.read()))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        elif file_ext == 'txt':
            return uploaded_file.read().decode('utf-8')
        else:
            return None
    except Exception as e:
        print(f"Error extrayendo texto: {e}")
        return None

def digest_document(text, cajon, subcajon):
    """
    Utiliza Gemma/Gemini para dividir el texto en chunks semánticos
    y generar un índice de conocimiento.
    """
    prompt = f"""
    Actúa como un Ingeniero de Conocimiento experto en IA. 
    Tu tarea es digerir el siguiente documento y prepararlo para un sistema RAG local.
    
    DOCUMENTO PARA PROCESAR:
    Categoría: {cajon} -> {subcajon}
    Texto: {text}
    
    INSTRUCCIONES DE DIGESTIÓN:
    1. Divide el texto en "chunks" (fragmentos) semánticos. Un chunk debe contener una idea completa.
    2. No cortes frases a la mitad.
    3. Para cada chunk, genera:
       - 'titulo': Un título breve y descriptivo.
       - 'contenido': El texto original del fragmento.
       - 'keywords': Una lista de 3-5 palabras clave para mejorar la búsqueda vectorial.
       - 'importancia': Un valor del 1 al 10 sobre la relevancia de este fragmento.
    
    FORMATO de SALIDA OBLIGATORIO: JSON puro, una lista de objetos.
    """
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return None
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error en digestión cloud: {e}")
        return None

def process_document_cloud(uploaded_file, cajon, subcajon):
    """Pipeline completo: Extracción -> Digestión Cloud."""
    text = extract_text(uploaded_file)
    if not text:
        return None, "No se pudo extraer texto del archivo."
    
    chunks = digest_document(text, cajon, subcajon)
    if not chunks:
        return None, "El procesador cloud no pudo digerir el documento."
    
    return chunks, None


def process_document_local(uploaded_file, cajon, subcajon, max_chars=1800):
    """Fragmentación local determinista: el documento nunca sale del equipo."""
    text = extract_text(uploaded_file)
    if not text:
        return None, "No se pudo extraer texto del archivo."
    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    chunks, current = [], []
    current_len = 0
    for paragraph in paragraphs:
        if current and current_len + len(paragraph) > max_chars:
            content = "\n\n".join(current)
            chunks.append({"titulo": f"{uploaded_file.name} · fragmento {len(chunks) + 1}",
                           "contenido": content, "keywords": [], "importancia": 5})
            current, current_len = [], 0
        current.append(paragraph)
        current_len += len(paragraph)
    if current:
        chunks.append({"titulo": f"{uploaded_file.name} · fragmento {len(chunks) + 1}",
                       "contenido": "\n\n".join(current), "keywords": [], "importancia": 5})
    return (chunks, None) if chunks else (None, "El documento no contiene texto utilizable.")
