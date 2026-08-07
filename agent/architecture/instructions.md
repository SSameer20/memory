# Engineering Rules

## General

- Keep classes small and focused.
- One responsibility per class.
- Prefer composition over inheritance.
- Avoid global state.
- Write readable code over clever code.
- Keep functions under ~50 lines when possible.

---

## SOLID

### Single Responsibility

- One class = one responsibility.
- One function = one task.

### Open/Closed

- Extend behavior through interfaces.
- Avoid modifying existing implementations.

### Liskov

- Every implementation should be interchangeable.

### Interface Segregation

- Keep interfaces small.
- Don't force unused methods.

### Dependency Inversion

- Depend on abstractions, not concrete implementations.

---

## Architecture

```
API
 ↓
Service
 ↓
Repository
 ↓
Database
```

- API handles HTTP only.
- Services contain business logic.
- Repositories access the database.
- Never skip layers.

---

## Dependency Injection

- Never instantiate dependencies inside services.
- Inject dependencies through constructors.
- Prefer FastAPI Depends() at the API layer.

Example

❌

```python
service = EmbeddingService()
```

✅

```python
def __init__(self, embedder: Embedder):
    self.embedder = embedder
```

---

## Repository Rules

Repositories should only:

- Create
- Read
- Update
- Delete

No business logic.

---

## Service Rules

Services should:

- Coordinate repositories
- Validate business rules
- Call external services
- Never contain SQL

---

## API Rules

Routes should:

- Validate requests
- Call services
- Return responses

Nothing else.

---

## Models

- ORM Models → Database
- Pydantic Models → API
- Never expose ORM models directly.

---

## Interfaces

Create interfaces for:

- Parser
- Embedder
- Vector Store
- Storage
- Reranker

Program against interfaces.

---

## Type Hints

Always type:

- Function parameters
- Return values
- Class attributes

Avoid `Any` unless necessary.

---

## Naming

Classes

- PascalCase

Functions

- snake_case

Variables

- snake_case

Constants

- UPPER_CASE

---

## Error Handling

- Raise domain-specific exceptions.
- Never swallow exceptions.
- Log meaningful errors.

---

## Logging

Log:

- Uploads
- Search requests
- Errors
- Processing time

Don't log sensitive data.

---

## Async

Use async only for:

- Database
- Network
- File I/O

Keep CPU-heavy work in background workers.

---

## Testing

Every service should be independently testable.

Mock:

- Database
- Vector DB
- LLM
- Storage

---

## Database

- Never write raw SQL in services.
- Use repositories.
- Use migrations for schema changes.
- Never use create_all() in production.

---

## Memory Service Rules

Upload Flow

```
Upload
→ Parse
→ Chunk
→ Embed
→ Store Metadata
→ Store Vectors
```

Search Flow

```
Query
→ Embed
→ Vector Search
→ Metadata Filter
→ Rerank
→ Build Context
→ Generate Citations
```

---

## Code Quality

- Keep methods focused.
- Avoid duplicate code.
- Prefer explicit over implicit.
- Use meaningful names.
- Add docstrings for public classes and methods.

---

## Rule of Thumb

If a class starts doing more than one job, split it.
If two classes change for different reasons, separate them.
If a dependency may change, hide it behind an interface.
