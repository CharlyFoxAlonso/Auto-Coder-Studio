import chromadb
from chromadb.config import Settings
import requests
import json
import os

# Configuración de Ollama para Embeddings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/embeddings")

def get_embedding(text):
    """Convierte texto en un vector usando el modelo nomic-embed-text de Ollama."""
    try:
        response = requests.post(
            OLLAMA_URL,
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
    return chromadb.PersistentClient(path="./chroma_db")

def indexar_chunks(chunks, cajon, subcajon):
    """
    Guarda los fragmentos procesados en la base de datos vectorial.
    """
    db = iniciar_db()
    # Creamos una colección por cada sub-cajón para máxima velocidad
    collection_name = f"{cajon}_{subcajon}".replace(" ", "_").lower()
    collection = db.get_or_create_collection(name=collection_name)

    for i, chunk in enumerate(chunks):
        # Combinamos título + contenido para el embedding
        texto_para_vector = f"{chunk['titulo']}\n{chunk['contenido']}"
        vector = get_embedding(texto_para_vector)
        
        if vector:
            collection.add(
                ids=[f"doc_{i}"],
                embeddings=[vector],
                metadatas=[{
                    "titulo": chunk['titulo'],
                    "cajon": cajon,
                    "subcajon": subcajon,
                    "importancia": chunk.get('importancia', 5)
                }],
                documents=[chunk['contenido']]
            )
    return True

def buscar_conocimiento(query, cajon=None, subcajon=None):
    """
    Busca los fragmentos más relevantes para una pregunta.
    """
    db = iniciar_db()
    
    # Si el usuario especificó cajones, buscamos solo ahí
    if cajon and subcajon:
        collection_name = f"{cajon}_{subcajon}".replace(" ", "_").lower()
        collection = db.get_or_create_collection(name=collection_name)
    else:
        # Si no, buscamos en todas las colecciones (simplicidad)
        # Nota: Para buscar en todas, tendríamos que iterar las colecciones.
        # Por simplicidad inicial, buscamos en el cajón general.
        collection = db.get_or_create_collection(name="general")

    query_vector = get_embedding(query)
    if not query_vector:
        return "Error al generar vector de búsqueda."

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=3
    )

    # Formateamos los resultados para el agente
    contexto = []
    for i in range(len(results['documents'][0])):
        doc = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        contexto.append(f"--- Fragmento ({meta['titulo']}) ---\n{doc}")

    return "\n\n".join(contexto) if contexto else "No se encontró información relevante en la biblioteca."
