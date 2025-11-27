# Quick Start: Supabase Integration

## Setup (5 minutes)

### 1. Apply Migration to Supabase

Go to: https://supabase.com/dashboard/project/gxpcrohsbtndndypagie/sql

Copy and run this SQL:

```sql
-- Enable pgvector extension
create extension if not exists vector with schema extensions;

-- Create vector similarity search function
create or replace function match_conductor_sessions (
  query_embedding extensions.vector,
  match_threshold float default 0.0,
  match_count int default 5
) returns table (
  id text,
  metadata jsonb,
  vec extensions.vector,
  similarity float
) language sql stable as $$
  select
    conductor_sessions.id,
    conductor_sessions.metadata,
    conductor_sessions.vec,
    1 - (conductor_sessions.vec <=> query_embedding) as similarity
  from vecs.conductor_sessions
  where 1 - (conductor_sessions.vec <=> query_embedding) > match_threshold
  order by (conductor_sessions.vec <=> query_embedding) asc
  limit match_count;
$$;

-- Create HNSW index for fast search
do $$
begin
    if not exists (
        select 1 from pg_indexes
        where schemaname = 'vecs'
        and tablename = 'conductor_sessions'
        and indexname = 'conductor_sessions_vec_idx'
    ) then
        create index conductor_sessions_vec_idx
        on vecs.conductor_sessions
        using hnsw (vec extensions.vector_cosine_ops)
        with (m = 16, ef_construction = 64);
    end if;
end $$;

-- Grant permissions
grant execute on function match_conductor_sessions(extensions.vector, float, int) to authenticated, anon;
```

### 2. Verify Setup

```bash
cd /Users/noahdeskin/conductor/queryable-slack-2/.conductor/doha
source .venv/bin/activate
python3 supabase/test_connection.py
```

You should see: ✅ ALL TESTS PASSED!

## Usage

### Basic Query

```python
from conductor.supabase_query import query_vector_similarity
import numpy as np

# Your query embedding (384 or 1536 dimensions)
query_embedding = np.random.random(384).tolist()

# Search
results = query_vector_similarity(
    query_embedding=query_embedding,
    match_threshold=0.7,
    match_count=10
)

# Results
for i, session_id in enumerate(results['ids'][0]):
    print(f"Session: {session_id}")
    print(f"Similarity: {1 - results['distances'][0][i]:.4f}")
```

## Troubleshooting

### "Table not found in public schema"

Your table is in `vecs` schema. Create a view:

```sql
CREATE VIEW public.conductor_sessions AS
SELECT * FROM vecs.conductor_sessions;
```

Or update the RPC function to reference `vecs.conductor_sessions` (already done in migration above).

### "RPC function does not exist"

Run the migration SQL from Step 1 above.

### "No results found"

The table might be empty. Run ingestion to populate it.

## Documentation

- Full docs: `supabase/README.md`
- Summary: `SUPABASE_INTEGRATION_SUMMARY.md`
- API reference: See `conductor/supabase_query.py` docstrings

## Help

Run the test script for diagnostics:
```bash
python3 supabase/test_connection.py
```

Error messages include actionable solutions.
