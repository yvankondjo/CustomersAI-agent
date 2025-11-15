# Supabase Migrations - Standard Operating Procedures

**Related docs:** [database_schema.md](../System/database_schema.md), [development_workflow.md](./development_workflow.md)

---

## 🎯 Purpose

This document explains how to create, apply, and manage database migrations using Supabase.

---

## 🛠️ Setup

### Using Supabase MCP (Recommended for Hackathon)

Since we have Supabase MCP configured (`.mcp.json`), we can use the MCP tools directly:

**Available MCP Tools:**
- `mcp__supabase__list_tables` - List all tables
- `mcp__supabase__apply_migration` - Create and apply migration
- `mcp__supabase__execute_sql` - Execute SQL (for queries, not DDL)
- `mcp__supabase__list_migrations` - List migration history

---

## 📝 Creating Migrations

### Method 1: Using MCP (Easiest)

**Example: Create initial schema**

```sql
-- Migration: initial_schema
-- Creates core tables for the platform

-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    website_url VARCHAR(500),
    contact_email VARCHAR(255),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

-- Social accounts table
CREATE TABLE IF NOT EXISTS social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    account_username VARCHAR(255),
    access_token TEXT,
    token_expires_at TIMESTAMPTZ,
    webhook_verify_token VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, account_id)
);

CREATE INDEX idx_social_accounts_tenant ON social_accounts(tenant_id);
CREATE INDEX idx_social_accounts_platform ON social_accounts(platform, account_id);

ALTER TABLE social_accounts ENABLE ROW LEVEL SECURITY;

-- Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, user_id, channel)
);

CREATE INDEX idx_conversations_tenant ON conversations(tenant_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Messages table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id, created_at);
CREATE INDEX idx_messages_created ON conversation_messages(created_at DESC);

ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
```

**Apply using MCP:**
```
Use mcp__supabase__apply_migration tool with:
- name: "initial_schema"
- query: <SQL above>
```

---

### Method 2: Using Supabase CLI (Alternative)

**Install CLI:**
```bash
npm install -g supabase
```

**Login:**
```bash
supabase login
```

**Link Project:**
```bash
supabase link --project-ref kttpamevcntespkhnijx
```

**Create Migration:**
```bash
supabase migration new initial_schema
```

This creates a file: `supabase/migrations/<timestamp>_initial_schema.sql`

**Write SQL in the file, then apply:**
```bash
supabase db push
```

---

## 🔄 Migration Best Practices

### 1. Always Use Transactions

**Good:**
```sql
BEGIN;

CREATE TABLE users (...);
CREATE INDEX idx_users_email ON users(email);

COMMIT;
```

**Why:** If any part fails, entire migration rolls back.

---

### 2. Use IF NOT EXISTS

**Good:**
```sql
CREATE TABLE IF NOT EXISTS users (...);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

**Why:** Prevents errors if migration runs twice.

---

### 3. Make Migrations Reversible (when possible)

**Create a "down" migration:**

**Up Migration (add_escalations_table):**
```sql
CREATE TABLE escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    reason VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Down Migration (remove_escalations_table):**
```sql
DROP TABLE IF EXISTS escalations;
```

---

### 4. Never Modify Existing Migrations

**❌ Bad:**
```sql
-- Editing supabase/migrations/001_initial_schema.sql after it's applied
ALTER TABLE users ADD COLUMN age INTEGER;  -- Don't do this!
```

**✅ Good:**
```sql
-- Create new migration: 002_add_user_age.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS age INTEGER;
```

---

### 5. Test Migrations Locally First

**Use Supabase local dev:**
```bash
supabase start  # Starts local Postgres
supabase db reset  # Resets DB and applies migrations
```

---

## 📋 Common Migration Patterns

### Adding a New Table

```sql
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_tenant ON documents(tenant_id);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Users can view their tenant's documents"
ON documents FOR SELECT
USING (tenant_id IN (
    SELECT tenant_id FROM user_tenants WHERE user_id = auth.uid()
));
```

---

### Adding a Column

```sql
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50);

-- Update existing rows (optional)
UPDATE conversations
SET sentiment = 'neutral'
WHERE sentiment IS NULL;
```

---

### Creating an Index

```sql
CREATE INDEX IF NOT EXISTS idx_messages_role
ON conversation_messages(role);
```

---

### Modifying a Column (Careful!)

```sql
-- Change column type (may require data migration)
ALTER TABLE conversations
ALTER COLUMN status TYPE VARCHAR(100);

-- Add constraint
ALTER TABLE conversations
ADD CONSTRAINT check_status
CHECK (status IN ('open', 'resolved', 'escalated'));
```

---

### Adding Foreign Key

```sql
ALTER TABLE escalations
ADD CONSTRAINT fk_escalations_conversation
FOREIGN KEY (conversation_id)
REFERENCES conversations(id)
ON DELETE CASCADE;
```

---

### Creating RLS Policies

```sql
-- Enable RLS
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their tenant's conversations
CREATE POLICY "tenant_isolation"
ON conversations FOR SELECT
USING (
  tenant_id IN (
    SELECT tenant_id FROM user_tenants WHERE user_id = auth.uid()
  )
);

-- Policy: Users can insert into their tenant
CREATE POLICY "tenant_insert"
ON conversations FOR INSERT
WITH CHECK (
  tenant_id IN (
    SELECT tenant_id FROM user_tenants WHERE user_id = auth.uid()
  )
);
```

---

## 🐛 Troubleshooting

### Migration Fails Halfway

**Problem:**
Migration applied partially, database in inconsistent state.

**Solution:**
```sql
-- Manually rollback the failed parts
DROP TABLE IF EXISTS problematic_table;

-- Fix the migration SQL
-- Reapply
```

---

### Duplicate Key Errors

**Problem:**
```
ERROR: duplicate key value violates unique constraint
```

**Solution:**
```sql
-- Add IF NOT EXISTS
CREATE TABLE IF NOT EXISTS users (...);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

---

### Foreign Key Violations

**Problem:**
```
ERROR: insert or update on table violates foreign key constraint
```

**Solution:**
1. Ensure referenced table exists first
2. Create tables in correct order
3. Use `ON DELETE CASCADE` if appropriate

---

### RLS Blocking Queries

**Problem:**
Queries return no results even though data exists.

**Solution:**
```sql
-- Check RLS is enabled
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- View policies
SELECT * FROM pg_policies WHERE tablename = 'conversations';

-- Temporarily disable for testing (local only!)
ALTER TABLE conversations DISABLE ROW LEVEL SECURITY;
```

---

## 📊 Checking Migration Status

### Using MCP

```
Use mcp__supabase__list_migrations to see all applied migrations
```

### Using Supabase CLI

```bash
supabase migration list
```

**Output:**
```
Applied migrations:
  001_initial_schema (2025-11-15 10:30:00)
  002_add_escalations (2025-11-15 11:00:00)

Pending migrations:
  003_add_topics_table
```

---

## 🔐 Security Considerations

### Always Enable RLS

```sql
-- Enable for all tables
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
```

### Create Restrictive Policies

```sql
-- Default deny everything
CREATE POLICY "deny_all" ON conversations FOR ALL USING (false);

-- Then explicitly allow what's needed
CREATE POLICY "allow_tenant_select" ON conversations FOR SELECT
USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

---

## 📝 Migration Checklist

Before applying a migration:

- [ ] Reviewed SQL syntax
- [ ] Used `IF NOT EXISTS` where appropriate
- [ ] Tested locally (if using Supabase CLI)
- [ ] Checked for data migration needs
- [ ] Enabled RLS on new tables
- [ ] Created appropriate indexes
- [ ] Added RLS policies
- [ ] Documented migration purpose
- [ ] Considered rollback plan

---

## 🔗 Quick Reference

### Essential SQL Commands

```sql
-- List tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Describe table
\d table_name  -- (psql only)

-- Or use information_schema
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'conversations';

-- Check indexes
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = 'conversations';

-- Check foreign keys
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f' AND conrelid::regclass::text = 'conversations';

-- View RLS policies
SELECT * FROM pg_policies WHERE tablename = 'conversations';
```

---

## 🔗 Related Documentation
- [Database Schema](../System/database_schema.md)
- [Development Workflow](./development_workflow.md)
- [Project Architecture](../System/project_architecture.md)
