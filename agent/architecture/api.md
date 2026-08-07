1. Documents

Handles document lifecycle.

```
POST   /documents                 Upload document

GET    /documents                 List documents

GET    /documents/{id}            Get document

PATCH  /documents/{id}            Update metadata

DELETE /documents/{id}            Delete document

POST   /documents/{id}/reindex    Re-index document

GET    /documents/{id}/chunks     Get chunks

GET    /documents/{id}/status     Processing status
```

2. Search

Main retrieval endpoint.

```
POST   /search

POST   /search/hybrid

POST   /search/semantic

POST   /search/keyword

POST   /search/image

POST   /search/audio
```

3. Memory

Higher-level abstraction over search.

```
POST   /memory/query

POST   /memory/context

POST   /memory/chat
```

4. Embeddings

Mostly for debugging/admin.

```
POST   /embeddings/generate

GET    /embeddings/models

POST   /embeddings/rebuild
```

5. Jobs

Since ingestion is asynchronous.

```
GET /jobs

GET /jobs/{id}

DELETE /jobs/{id}
```

6 Stats

```
GET /stats

GET /stats/documents

GET /stats/chunks

GET /stats/search
```
