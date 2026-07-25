import chromadb
from chromadb.config import Settings
import requests
import os
import re
import uuid
from pathlib import Path

# Configuración de Ollama para Embeddings
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
RAG_DB_PATH = Path(__file__).resolve().parent.parent / ".autocoder" / "chroma_db"

def get_embedding(text):
    """Convierte texto en un vector usando el modelo nomic-embed-text de Ollama."""
    try:
        response = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception as e:
        print(f"Error generando embedding: {e}")
        return None

def iniciar_db():
    """Inicia el cliente de ChromaDB persistente."""
    RAG_DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(RAG_DB_PATH))


def _collection_name(cajon, subcajon):
    raw = f"{cajon}_{subcajon}".lower()
    clean = re.sub(r"[^a-z0-9._-]+", "_", raw).strip("._-")
    return (clean or "general")[:63]

def indexar_chunks(chunks, cajon, subcajon):
    """
    Guarda los fragmentos procesados en la base de datos vectorial.
    """
    db = iniciar_db()
    # Creamos una colección por cada sub-cajón para máxima velocidad
    collection_name = _collection_name(cajon, subcajon)
    collection = db.get_or_create_collection(name=collection_name)

    indexed = 0
    for i, chunk in enumerate(chunks):
        # Combinamos título + contenido para el embedding
        texto_para_vector = f"{chunk['titulo']}\n{chunk['contenido']}"
        vector = get_embedding(texto_para_vector)
        
        if vector:
            collection.add(
                ids=[f"doc_{uuid.uuid4().hex}"],
                embeddings=[vector],
                metadatas=[{
                    "titulo": chunk['titulo'],
                    "cajon": cajon,
                    "subcajon": subcajon,
                    "importancia": chunk.get('importancia', 5)
                }],
                documents=[chunk['contenido']]
            )
            indexed += 1
    return indexed == len(chunks) and indexed > 0

def buscar_conocimiento(query, cajon=None, subcajon=None):
    """
    Busca los fragmentos más relevantes para una pregunta.
    """
    db = iniciar_db()
    
    # Si el usuario especificó cajones, buscamos solo ahí
    if cajon and subcajon:
        collections = [db.get_or_create_collection(name=_collection_name(cajon, subcajon))]
    else:
        collections = db.list_collections()

    query_vector = get_embedding(query)
    if not query_vector:
        return "Error al generar vector de búsqueda."

    candidatos = []
    for collection in collections:
        if collection.count() == 0:
            continue
        results = collection.query(query_embeddings=[query_vector], n_results=min(3, collection.count()))
        distances = results.get("distances", [[]])[0]
        for i, doc in enumerate(results.get('documents', [[]])[0]):
            meta = results.get('metadatas', [[]])[0][i]
            distance = distances[i] if i < len(distances) else 999
            candidatos.append((distance, meta, doc))

    contexto = [f"--- Fragmento ({meta.get('titulo', 'Sin título')}) ---\n{doc}"
                for _, meta, doc in sorted(candidatos, key=lambda item: item[0])[:3]]

    return "\n\n".join(contexto) if contexto else "No se encontró información relevante en la biblioteca."
