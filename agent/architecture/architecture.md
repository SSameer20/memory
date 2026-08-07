# Memory Service

## Overview

Memory Service is a standalone platform that enables AI agents and applications to store, search, and retrieve multimodal knowledge.

The service supports PDFs, text, markdown, images, and audio (video support planned). Applications integrate with the service through APIs without implementing their own RAG pipeline.

The platform provides:

- Document ingestion
- Metadata management
- Chunk generation
- Embedding generation
- Vector search
- Citation generation
- Semantic retrieval
- Project isolation
- Low-latency querying

---

# Goals

- Simple API for storing memory
- High quality retrieval
- Source citations
- Multi-modal support
- Easy integration into existing AI systems
- Horizontally scalable

---

# Functional Requirements

## User Management

- Create user
- Authentication
- API Keys
- Multi-tenant isolation

---

## Project Management

A user can own multiple projects.

Each project has independent memory.

Example

User
├── Project A
├── Project B
├── Project C

Searching Project A never returns documents from Project B.

---

## Document Management

Supported types

- PDF
- TXT
- Markdown
- Images
- Audio
- Video (future)

Operations

- Upload
- Delete
- Update
- Version documents
- Soft delete
- Bulk upload

---

## Metadata

Every document contains

- document_id
- project_id
- user_id
- filename
- mime_type
- tags
- upload_time
- language
- source
- checksum
- status

---

## Parsing

Extract content according to file type.

PDF

- OCR if required
- Table extraction
- Image extraction
- Layout preservation

Text

- Preserve headings
- Preserve markdown
- Preserve code blocks

Image

- OCR
- Caption generation
- Object extraction

Audio

- Speech-to-text
- Speaker detection
- Timestamp generation

---

## Chunking

Generate semantic chunks.

Support multiple strategies

- Recursive chunking
- Markdown aware
- Semantic chunking
- Table chunking
- Code chunking

Chunk metadata

- page number
- section
- heading
- chunk id
- parent document
- token count

---

## Embedding

Generate embeddings for

- text
- image
- audio transcript

Support multiple providers

- OpenAI
- Voyage
- Gemini
- Jina
- BGE

Embeddings should be versioned.

---

## Storage

Raw Storage

Stores

- Original files
- OCR output
- Images

Metadata Database

Stores

- Users
- Projects
- Documents
- Chunks

Vector Database

Stores

- Embeddings
- Chunk references

---

## Retrieval

Query

↓

Embedding Generation

↓

Semantic Cache

↓

Vector Search

↓

Metadata Filter

↓

Hybrid Search

↓

Reranking

↓

Context Assembly

↓

Citation Generation

↓

Return to LLM

---

## Search Features

Support

- Semantic search
- Hybrid search
- Metadata filtering
- Tag filtering
- Date filtering
- Project filtering
- File filtering

---

## Citation

Every response contains

- filename
- page
- chunk
- confidence score

---

## APIs

### Project

POST /projects

GET /projects

DELETE /projects

---

### Documents

POST /documents

DELETE /documents/{id}

PATCH /documents/{id}

GET /documents

---

### Search

POST /search

---

### Memory

POST /memory

GET /memory

DELETE /memory

---

# Non Functional Requirements

## Performance

Upload latency

< 5 seconds for average document

Search latency

< 300ms without LLM

< 2 seconds with reranking

---

## Scalability

Support

- Millions of chunks
- Thousands of projects
- Concurrent uploads
- Horizontal scaling

---

## Reliability

- Retry failed ingestion
- Dead Letter Queue
- Idempotent uploads
- Background workers

---

## Availability

99.9% uptime

---

## Security

- Authentication
- Authorization
- Project isolation
- Encryption at rest
- HTTPS
- Signed URLs

---

## Observability

Metrics

- Upload latency
- Search latency
- Chunk count
- Cache hit rate
- Embedding latency

Logging

- API logs
- Retrieval logs
- Errors

Tracing

- End-to-end request tracing

---

# Architecture

```text
                Client
                   │
             REST API Gateway
                   │
         ┌─────────┴─────────┐
         │                   │
     Upload API          Search API
         │                   │
         │             Query Embedding
         │                   │
    Ingestion Queue      Semantic Cache
         │                   │

File Classifier Vector Search
│ │
File Parser Metadata Filter
│ │
Chunk Generator Hybrid Search
│ │
Embedding Service Reranker
│ │
└──────► Context Builder
│
Citation Builder
│
Response
```

---

# Storage

Object Storage

- Original files
- Images
- Audio

Metadata DB

- PostgreSQL

Vector DB

- Qdrant
- Weaviate
- Pinecone

Cache

- Redis

Queue

- RabbitMQ
- Kafka
- SQS

---

# Things Missing in Current Design

## Authentication

Currently absent.

Need

- JWT
- API Keys
- Multi-tenant support

---

## Background Workers

Uploads should never block API requests.

Move ingestion into async workers.

---

## Retry Mechanism

Failed OCR

↓

Retry

↓

Dead Letter Queue

---

## Hybrid Search

Current design uses only embeddings.

Add

BM25

-

Vector Search

This greatly improves retrieval quality.

---

## Reranker

Very important.

Instead of

Top 20 Vector Results

↓

LLM

Use

Top 50

↓

Cross Encoder

↓

Top 5

↓

LLM

---

## Metadata Filters

Support

- project
- filename
- tags
- date
- owner

---

## Cache

Add

- Embedding cache
- Semantic cache
- Search cache

---

## Versioning

Documents should support updates.

Instead of replacing,

Maintain versions.

---

## Observability

Need

- OpenTelemetry
- Prometheus
- Grafana

---

## Evaluation Pipeline

Measure retrieval quality.

Metrics

- Recall@K
- Precision@K
- MRR
- nDCG

Do not rely only on manual testing.

---

## Cost Optimization

- Batch embeddings
- Cache embeddings
- Compress chunks
- Adaptive chunk size
- Async ingestion
- Deduplicate identical documents

---

# Future Roadmap

Phase 1

- Text
- PDF
- Basic RAG

Phase 2

- OCR
- Images
- Audio
- Hybrid Search

Phase 3

- Video
- Knowledge Graph
- Agent Memory
- Temporal Memory
- Memory Sharing

Phase 4

- Incremental indexing
- Event-driven ingestion
- Multi-region deployment
- Enterprise access control
