# Système d'Ingestion - Documentation

## Vue d'ensemble

Le système d'ingestion permet de traiter des documents et des sites web pour alimenter la base de connaissances RAG. Il utilise Redis Queue (RQ) pour le traitement asynchrone.

## Architecture

- **Routes FastAPI** : `/api/v1/ingestion/document` et `/api/v1/ingestion/website`
- **Workers RQ** : Traitement asynchrone dans des queues séparées
- **Qdrant** : Stockage des embeddings (filtrage par `user_id`)
- **Gemini** : Génération des embeddings (1536 dimensions)

## Installation

### Dépendances

```bash
pip install redis rq crawl4ai
```

### Variables d'environnement

```env
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your_gemini_api_key
MISTRAL_API_KEY=your_mistral_api_key
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key
```

## Démarrage

### 1. Démarrer Redis

```bash
redis-server
```

### 2. Démarrer les workers

```bash
python backend/start_workers.py
```

Ou avec RQ directement :

```bash
rq worker --url redis://localhost:6379/0 documents websites
```

### 3. Démarrer l'API FastAPI

```bash
uvicorn app.main:app --reload
```

## Utilisation

### Ingestion de document

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-uuid",
    "user_id": "user-uuid"
  }'
```

Réponse :
```json
{
  "status": "queued",
  "job_id": "job-uuid",
  "message": "Document ingestion queued successfully"
}
```

### Ingestion de site web

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/website \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "user_id": "user-uuid",
    "max_pages": 20
  }'
```

Réponse :
```json
{
  "status": "queued",
  "job_id": "job-uuid",
  "message": "Website ingestion queued successfully"
}
```

### Vérifier le statut d'un job

```bash
curl http://localhost:8000/api/v1/ingestion/job/{job_id}
```

Réponse :
```json
{
  "job_id": "job-uuid",
  "status": "finished",
  "result": {"status": "success", "document_id": "doc-uuid"},
  "error": null,
  "created_at": "2025-01-15T10:00:00",
  "started_at": "2025-01-15T10:00:01",
  "ended_at": "2025-01-15T10:02:30"
}
```

## Queues

- **`documents`** : Traitement des documents (PDF, Word, etc.)
  - Plusieurs documents peuvent être traités en parallèle
  - Timeout : 30 minutes

- **`websites`** : Traitement des sites web
  - Un seul site à la fois (sérialisé)
  - Timeout : 1 heure
  - Paramètre `max_pages` : 1-100 (défaut: 50)

## Tests

```bash
pytest backend/tests/test_ingestion.py -v
```

## Notes importantes

1. **Documents** : Les documents doivent exister dans la table `documents` ou `knowledge_documents`
2. **Sites web** : Utilise Crawl4AI pour le crawling (gère JavaScript)
3. **Embeddings** : Stockés uniquement dans Qdrant avec `user_id` pour filtrage
4. **Chunking** : Respecte les blocs de code et paragraphes
5. **Titres/Résumés** : Générés avec Mistral AI pour chaque chunk

