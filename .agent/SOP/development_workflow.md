# Development Workflow - Standard Operating Procedures

**Related docs:** [project_architecture.md](../System/project_architecture.md), [supabase_migrations.md](./supabase_migrations.md)

---

## 🎯 Purpose

This document outlines best practices for developing, testing, and deploying the AI Customer Support Platform.

---

## 🚀 Getting Started

### Initial Setup

**1. Clone Repository:**
```bash
git clone https://github.com/your-org/customer-ai-agent.git
cd customer-ai-agent
```

**2. Setup Backend:**
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

**3. Setup Frontend:**
```bash
cd frontend
npm install
```

**4. Environment Variables:**

Create `.env` files:

**Backend `.env`:**
```env
# Supabase
SUPABASE_URL=https://kttpamevcntespkhnijx.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_api_key

# OpenAI/OpenRouter
OPENAI_API_KEY=your_openrouter_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Models
DEFAULT_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small

# App Config
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Frontend `.env.local`:**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://kttpamevcntespkhnijx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

**5. Initialize Database:**
```bash
# See: supabase_migrations.md
```

**6. Run Development Servers:**

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

---

## 📂 Project Structure

### Backend Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + routes
│   ├── config.py            # Settings (env vars)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── router.py        # LangGraph router
│   │   └── nodes.py         # Agent nodes (FAQ, RAG, etc.)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag.py           # RAG pipeline
│   │   ├── embedding.py     # Embeddings service
│   │   ├── crawler.py       # Crawl4AI integration
│   │   └── supabase_client.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   └── workers/             # Background workers
│       ├── __init__.py
│       ├── escalation.py
│       └── ingestion.py
├── scripts/
│   └── seed_knowledge.py    # Test data seeding
├── tests/
│   ├── __init__.py
│   ├── test_rag.py
│   └── test_api.py
├── requirements.txt
└── .env
```

### Frontend Structure
```
frontend/
├── app/
│   ├── page.tsx             # Home/chat page
│   ├── layout.tsx
│   └── admin/
│       └── conversations/
│           └── page.tsx
├── components/
│   ├── ChatWidget.tsx
│   ├── MessageList.tsx
│   └── ConversationList.tsx
├── lib/
│   ├── api.ts               # API client
│   └── supabase.ts
├── public/
│   └── widget.js            # Embeddable widget
├── package.json
└── .env.local
```

---

## 🔄 Development Workflow

### 1. Feature Development

**Step 1: Create Feature Branch**
```bash
git checkout -b feature/add-escalation-email
```

**Step 2: Implement Feature**
- Write code
- Follow code style guidelines (see below)
- Add docstrings/comments

**Step 3: Test Locally**
```bash
# Backend tests
cd backend
pytest

# Frontend (if applicable)
cd frontend
npm run build
```

**Step 4: Commit Changes**
```bash
git add .
git commit -m "feat: add email escalation for complex issues

- Implement escalation worker
- Add email template
- Store escalations in DB
- Update routing logic"
```

**Commit Message Format:**
```
<type>: <short description>

<longer description if needed>

<footer (breaking changes, etc.)>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance

**Step 5: Push & Create PR**
```bash
git push origin feature/add-escalation-email
```

Then create Pull Request on GitHub.

---

### 2. Code Review Process

**Reviewer Checklist:**
- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] No obvious bugs
- [ ] Documentation updated (if needed)
- [ ] No breaking changes (or flagged)
- [ ] Performance considerations reviewed

**Required Reviewers:** 1 (for hackathon), 2+ (production)

---

### 3. Merging to Main

**Only merge when:**
- [ ] All tests pass
- [ ] Code reviewed and approved
- [ ] No merge conflicts
- [ ] Documentation updated

**Merge Strategy:** Squash and merge (keep clean history)

---

## 🧪 Testing Guidelines

### Backend Tests

**Unit Tests (pytest):**
```python
# tests/test_rag.py
import pytest
from app.services.rag import search_knowledge, format_rag_context

@pytest.mark.asyncio
async def test_search_knowledge():
    """Test RAG search returns results."""
    results = await search_knowledge(
        query="délai livraison",
        tenant_id="test-tenant",
        top_k=3
    )

    assert len(results) <= 3
    assert all("content" in r for r in results)
    assert all("score" in r for r in results)

def test_format_rag_context():
    """Test context formatting."""
    chunks = [
        {
            "content": "Test content 1",
            "metadata": {"url": "https://example.com/page1"}
        },
        {
            "content": "Test content 2",
            "metadata": {"filename": "doc.pdf"}
        }
    ]

    context = format_rag_context(chunks)

    assert "Source 1" in context
    assert "Source 2" in context
    assert "Test content 1" in context
```

**Run Tests:**
```bash
cd backend
pytest
pytest --cov=app  # with coverage
```

---

### Frontend Tests

**Component Tests (Jest + React Testing Library):**
```typescript
// __tests__/ChatWidget.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import ChatWidget from '@/components/ChatWidget'

describe('ChatWidget', () => {
  it('renders chat input', () => {
    render(<ChatWidget />)
    expect(screen.getByPlaceholderText(/type a message/i)).toBeInTheDocument()
  })

  it('sends message on button click', async () => {
    render(<ChatWidget />)

    const input = screen.getByPlaceholderText(/type a message/i)
    const button = screen.getByRole('button', { name: /send/i })

    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.click(button)

    // Assert message sent
  })
})
```

**Run Tests:**
```bash
cd frontend
npm test
```

---

### Integration Tests

**API Integration Tests:**
```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_support_message_flow():
    """Test full message flow."""
    response = client.post("/api/v1/support/message", json={
        "tenant_id": "test-tenant",
        "user_id": "user-123",
        "channel": "widget",
        "content": "Quel est le délai de livraison ?"
    })

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "livraison" in data["response"].lower()
```

---

## 📝 Code Style Guidelines

### Python (Backend)

**Follow PEP 8:**
```python
# Good
def search_knowledge(query: str, tenant_id: str, top_k: int = 3) -> list[dict]:
    """Search knowledge base with filtering.

    Args:
        query: User's search query
        tenant_id: Tenant ID for filtering
        top_k: Number of results to return

    Returns:
        List of search results with content and metadata
    """
    # Implementation
    pass

# Bad
def searchKnowledge(query,tenant_id,top_k=3):
    # No docstring, bad naming, missing types
    pass
```

**Use Type Hints:**
```python
# Always use type hints
async def embed_text(text: str) -> list[float]:
    ...

# For complex types
from typing import Optional, Union
def get_conversation(id: str) -> Optional[dict]:
    ...
```

**Formatting:**
```bash
# Use Black for auto-formatting
pip install black
black app/

# Use isort for imports
pip install isort
isort app/
```

---

### TypeScript (Frontend)

**Follow TypeScript Best Practices:**
```typescript
// Good
interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
}

async function sendMessage(message: Message): Promise<Response> {
  // Implementation
}

// Bad
function sendMessage(message: any) {
  // No types, no async/await clarity
}
```

**Component Structure:**
```typescript
// components/ChatWidget.tsx
'use client'

import { useState } from 'react'

interface ChatWidgetProps {
  tenantId: string
  initialMessages?: Message[]
}

export default function ChatWidget({ tenantId, initialMessages = [] }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)

  // Component logic
  return (
    <div>
      {/* JSX */}
    </div>
  )
}
```

---

## 🐛 Debugging

### Backend Debugging

**Enable Debug Logs:**
```python
# app/config.py
import logging

logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Use pdb for Breakpoints:**
```python
import pdb; pdb.set_trace()  # Add breakpoint

# Or use ipdb (better)
import ipdb; ipdb.set_trace()
```

**VS Code Debug Config:**
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

---

### Frontend Debugging

**Browser DevTools:**
- Console logs
- Network tab (check API calls)
- React DevTools extension

**Debug API Calls:**
```typescript
// lib/api.ts
export async function sendMessage(data: MessageRequest) {
  console.log('Sending message:', data)  // Debug log

  const response = await fetch('/api/v1/support/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })

  const result = await response.json()
  console.log('Response:', result)  // Debug log

  return result
}
```

---

## 🚀 Deployment

### Backend Deployment (Railway/Render)

**1. Create `Procfile`:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**2. Requirements.txt:**
Ensure all dependencies listed.

**3. Environment Variables:**
Set all env vars in hosting platform dashboard.

**4. Deploy:**
```bash
# Railway
railway up

# Or Render (auto-deploys from GitHub)
```

---

### Frontend Deployment (Vercel)

**1. Connect GitHub repo to Vercel**

**2. Set Environment Variables:**
```
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

**3. Deploy:**
Vercel auto-deploys on git push to main.

---

## 📊 Monitoring & Logs

### Production Monitoring

**Use Sentry for Errors:**
```python
# app/main.py
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    environment="production"
)
```

**Check Logs:**
```bash
# Railway
railway logs

# Render
# View in dashboard
```

---

## 🔒 Security Best Practices

1. **Never commit secrets:**
   - Use `.env` files
   - Add `.env` to `.gitignore`

2. **Use environment variables:**
   - API keys
   - Database credentials
   - Webhook tokens

3. **Validate input:**
   - Use Pydantic models
   - Sanitize user input
   - Prevent SQL injection (use ORMs)

4. **Enable RLS:**
   - Supabase Row Level Security
   - Filter by tenant_id

5. **Rate limiting:**
   - Use FastAPI middleware
   - Prevent API abuse

---

## 🔗 Related Documentation
- [Project Architecture](../System/project_architecture.md)
- [Supabase Migrations](./supabase_migrations.md)
- [Adding RAG Sources](./adding_rag_sources.md)
