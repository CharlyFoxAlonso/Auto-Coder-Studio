# AutoCoder Studio

Agente de programación autónomo con interfaz Streamlit. Conecta con Ollama, OpenAI o Anthropic para analizar, modificar y ejecutar código en un workspace local.

## Estado actual

- Explorador de workspace con selector de carpetas
- Chat con historial por sesiones
- Soporte multi-proveedor (Ollama, OpenAI, Anthropic)
- Acciones aprobadas por el usuario (write, delete, run)
- RAG local con ChromaDB
- Extensiones: comandos, skills y funciones reutilizables

## Visión (refactorización)

### 1. Explorar el repositorio linkeado

Que el coder pueda acceder al repositorio Git vinculado (detectar `.git`, leer historial, ramas, diffs) para tener contexto completo del proyecto y operar sobre archivos trackeados.

### 2. Creación múltiple de archivos

Permitir que el modelo genere varios archivos en una sola respuesta (lotes), con previsualización por archivo y aprobación opcional por lote completo.

### 3. Modo auto-aprobado (switch en interfaz)

Agregar un toggle en la interfaz que permita al modelo editar directamente en el repo seleccionado sin pedir autorización por cada creación. Ideal para tareas repetitivas o cuando se confía en el modelo.