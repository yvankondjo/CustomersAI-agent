# AI Customer Support Platform - Documentation Index

## 📚 Documentation Structure

This folder contains all critical documentation for the AI Customer Support & Automation Platform (Instagram + Web).

---

## 🗂️ Documentation Files

### System Documentation
Located in `.agent/System/`

- **[project_architecture.md](./System/project_architecture.md)**
  Complete system architecture including project goals, tech stack, integration points, and component design

- **[database_schema.md](./System/database_schema.md)**
  Full database schema with tables, relationships, and data models for Supabase

- **[rag_pipeline.md](./System/rag_pipeline.md)**
  RAG (Retrieval Augmented Generation) pipeline architecture with Qdrant, embeddings, and reranking strategy

---

### Tasks & Planning
Located in `.agent/Tasks/`

- **[prd.md](./Tasks/prd.md)**
  Complete Product Requirements Document with all features and specifications

- **[hackathon_roadmap.md](./Tasks/hackathon_roadmap.md)**
  Prioritized implementation plan for hackathon (12-hour sprint)

- **[mvp_features.md](./Tasks/mvp_features.md)**
  Minimum Viable Product feature breakdown with acceptance criteria

---

### Standard Operating Procedures
Located in `.agent/SOP/`

- **[development_workflow.md](./SOP/development_workflow.md)**
  Best practices for development, testing, and deployment

- **[supabase_migrations.md](./SOP/supabase_migrations.md)**
  How to create and apply database migrations

- **[adding_rag_sources.md](./SOP/adding_rag_sources.md)**
  How to add new knowledge sources (documents, websites, FAQs)

---

## 🚀 Quick Start Guide

### For New Engineers
1. Read **[project_architecture.md](./System/project_architecture.md)** to understand system design
2. Read **[database_schema.md](./System/database_schema.md)** to understand data models
3. Read **[hackathon_roadmap.md](./Tasks/hackathon_roadmap.md)** to see implementation priorities
4. Read **[development_workflow.md](./SOP/development_workflow.md)** for best practices

### For Product/Business
1. Read **[prd.md](./Tasks/prd.md)** for complete product vision
2. Read **[mvp_features.md](./Tasks/mvp_features.md)** for feature prioritization

### For Implementation
1. Follow **[hackathon_roadmap.md](./Tasks/hackathon_roadmap.md)** phase by phase
2. Reference **SOPs** for specific tasks (migrations, RAG sources, etc.)

---

## 📝 Documentation Maintenance

- **Always update docs after implementing features**
- **Keep database schema in sync with migrations**
- **Update roadmap as priorities change**
- **Add new SOPs for complex recurring tasks**

---

## 🔗 External Resources

- Supabase Project: `kttpamevcntespkhnijx`
- Tech Stack: FastAPI, LangGraph, Qdrant, Next.js, Supabase
- Key Tools: Crawl4AI, OpenRouter, BERTopic (optional)
