from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeKind(str, Enum):
    document = "document"
    section = "section"
    subsection = "subsection"
    paragraph = "paragraph"
    list = "list"
    list_item = "list_item"
    table = "table"
    figure = "figure"
    caption = "caption"
    code = "code"
    page_break = "page_break"
    unknown = "unknown"


class AstNode(BaseModel):
    node_id: str
    kind: NodeKind
    element_type: str
    text: str = ""
    title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    pages: list[int] = Field(default_factory=list)
    heading_path: list[str] = Field(default_factory=list)
    order: int = 0
    source_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    children: list["AstNode"] = Field(default_factory=list)


class ChunkMeta(BaseModel):
    chunk_id: str
    doc_id: str
    parent_chunk_id: str | None = None
    child_chunk_ids: list[str] = Field(default_factory=list)
    chunk_order: int = 0
    section: str | None = None
    subsection: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    element_types: list[str] = Field(default_factory=list)
    source_node_ids: list[str] = Field(default_factory=list)
    token_count: int | None = None
    char_count: int | None = None
    chunk_type: str = "structural"


class Chunk(BaseModel):
    text: str
    meta: ChunkMeta


class ProcessedDocument(BaseModel):
    document_id: str
    filename: str
    pdf_path: str
    docling_path: str | None = None
    ast_path: str | None = None
    chunks_path: str | None = None
    source_mode: str
    section_count: int = 0
    chunk_count: int = 0
    ast: AstNode
    chunks: list[Chunk]
    docling_document: dict[str, Any] | None = None
    summary: dict[str, Any] = Field(default_factory=dict)

