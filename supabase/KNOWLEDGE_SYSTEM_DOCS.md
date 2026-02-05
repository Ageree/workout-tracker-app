# Knowledge System Developer Documentation

## Overview

This document describes how to add, update, and manage scientific knowledge claims in the AI Coach knowledge base.

## Architecture

The knowledge system uses a hybrid approach:
- **Supabase PostgreSQL** with `pgvector` extension for semantic search
- **OpenAI Embeddings** (text-embedding-3-small) for vector representations
- **Swift Client** (iOS app) for AI Coach chat interface
- **Agent Swarm** (Python) for automated knowledge processing

### Agent Swarm Integration

The system includes an automated Agent Swarm for knowledge management:

```
┌─────────────────────────────────────────────────────────────┐
│                      AGENT SWARM                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Research   │───▶│  Extraction  │───▶│  Validation  │   │
│  │   Agent 🔍   │    │   Agent 📖   │    │   Agent ✅   │   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘   │
│         │                                        │           │
│         │         ┌──────────────┐              │           │
│         │         │   Conflict   │◀─────────────┘           │
│         │         │   Agent 🔄   │                          │
│         │         └──────┬───────┘                          │
│         │                │                                  │
│         │         ┌──────▼───────┐                          │
│         └────────▶│  Knowledge   │                          │
│                   │   Base 📚    │                          │
│                   └──────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**KB Agent (📚)** automatically processes pending embeddings:
- Polls for claims with `embedding_status = 'pending'`
- Generates embeddings via OpenAI API
- Updates status to `completed` or `failed`
- Updates evidence hierarchy

See [`README_AGENT_SWARM.md`](README_AGENT_SWARM.md) for details.

## Database Schema

### Main Tables

#### `scientific_knowledge`
Stores individual scientific claims extracted from research.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `claim` | TEXT | The scientific claim statement (RU) |
| `claim_summary` | TEXT | Short summary for display |
| `category` | TEXT | Category: hypertrophy, strength, nutrition, etc. |
| `evidence_level` | INT | 1-5 scale (1=expert opinion, 5=meta-analysis) |
| `confidence_score` | NUMERIC | 0-1 confidence in the claim |
| `status` | TEXT | active, deprecated, under_review, draft |
| `source_title` | TEXT | Original paper title |
| `source_authors` | TEXT[] | Array of author names |
| `source_doi` | TEXT | DOI link |
| `publication_date` | DATE | When published |
| `sample_size` | INT | Number of subjects in study |
| `study_design` | TEXT | meta_analysis, rct, cohort, etc. |
| `key_findings` | TEXT[] | Array of key findings |
| `limitations` | TEXT | Study limitations |
| `embedding` | VECTOR(1536) | OpenAI embedding for semantic search |
| `embedding_status` | TEXT | pending, processing, completed, failed |
| `embedding_error` | TEXT | Error message if embedding generation failed |

#### `research_queue`
Queue for papers to be processed.

#### `knowledge_feedback`
User feedback on AI responses.

#### `evidence_hierarchy`
Aggregated scores by topic.

## Adding New Knowledge Claims

### Method 1: Direct SQL Migration (Recommended for Bulk)

1. Create a new migration file in `supabase/migrations/`
2. Follow the format in `004_seed_knowledge_base.sql` or `006_add_more_knowledge.sql`
3. Run the migration

Example:
```sql
INSERT INTO public.scientific_knowledge (
  claim,
  claim_summary,
  category,
  evidence_level,
  confidence_score,
  status,
  source_title,
  source_authors,
  publication_date,
  sample_size,
  study_design,
  key_findings,
  limitations
) VALUES (
  'Your claim here in Russian',
  'Short summary',
  'hypertrophy', -- or strength, nutrition, etc.
  4, -- evidence level 1-5
  0.85, -- confidence 0-1
  'active',
  'Original Paper Title',
  ARRAY['Author Name'],
  '2020-01-01',
  100,
  'meta_analysis',
  ARRAY['Finding 1', 'Finding 2'],
  'Study limitations'
);
```

### Method 2: Generate Embeddings After Insert

After inserting claims without embeddings, run the Python script:

```bash
cd supabase
pip install -r requirements.txt

export OPENAI_API_KEY="your-key"
export SUPABASE_URL="your-url"
export SUPABASE_SERVICE_KEY="your-service-key"

# Dry run to see what would be processed
python generate_embeddings.py --dry-run

# Actually generate embeddings
python generate_embeddings.py

# Verify coverage
python generate_embeddings.py --verify

# Test semantic search
python generate_embeddings.py --test-search "протеин для мышц"
```

## Evidence Level Guidelines

Use this scale consistently:

| Level | Type | Description | Example |
|-------|------|-------------|---------|
| 5 | Meta-analysis | Pooled data from multiple studies | Schoenfeld meta-analysis |
| 4 | Systematic Review | Structured review of literature | ISSN position stand |
| 4 | RCT | Randomized controlled trial | Training study with groups |
| 3 | Controlled Trial | Non-randomized controlled | Cohort comparison |
| 2 | Observational | Cohort, cross-sectional | Epidemiological study |
| 1 | Expert Opinion | Expert consensus, case study | Position statement |

## Categories

Available categories:
- `hypertrophy` - Muscle growth
- `strength` - Strength development
- `endurance` - Cardiovascular/muscular endurance
- `nutrition` - Diet, supplements, meal timing
- `recovery` - Sleep, rest, deload
- `injury_prevention` - Warm-up, technique, load management
- `technique` - Exercise form, biomechanics
- `programming` - Periodization, volume, frequency
- `supplements` - Ergogenic aids
- `general` - Other topics

## Writing Good Claims

### DO:
- Write in Russian (app is Russian-language)
- Be specific with numbers ("6-30 reps" not "various rep ranges")
- Include effect sizes when known ("2-7% increase")
- Note limitations and context
- Use evidence-based sources (PubMed, peer-reviewed journals)

### DON'T:
- Make absolute statements ("always", "never")
- Use bro-science or anecdotal evidence
- Copy-paste abstracts - extract specific claims
- Include marketing claims from supplement companies

### Example Good Claims:
```
✓ "Для гипертрофии оптимальный диапазон повторений составляет 6-30 
    повторений в подходе при условии достижения мышечного отказа"
✓ "Креатин моногидрат увеличивает силу на 5-15% при длительном приёме"
```

### Example Bad Claims:
```
✗ "БЦАА необходимы для роста мышц" (too vague, not evidence-based)
✗ "Всегда делайте разминку 10 минут" (absolute, no context)
```

## Testing Knowledge Integration

### Test Semantic Search
```bash
python generate_embeddings.py --test-search "как набрать мышечную массу"
```

### Test in App
1. Build and run the iOS app
2. Ask a question related to your new claim
3. Check that relevant knowledge appears in the context
4. Verify the response references the scientific claim

## Updating Existing Claims

To update a claim without breaking history:

```sql
-- First, create a new version with updated info
INSERT INTO public.scientific_knowledge (...)
VALUES (...);

-- Then deprecate the old one
UPDATE public.scientific_knowledge
SET status = 'deprecated'
WHERE id = 'old-claim-uuid';
```

The versioning trigger will automatically create a history record.

## SQL Functions for AI Coach

The following SQL functions power the AI Coach knowledge system:

### `match_knowledge_vectors`
Semantic search using vector similarity.

```sql
SELECT * FROM match_knowledge_vectors(
  query_embedding := '[0.1, 0.2, ...]'::vector(1536),
  match_threshold := 0.7,
  match_count := 5,
  filter_category := 'hypertrophy',  -- optional
  min_evidence_level := 2
);
```

Returns: `id, claim, claim_summary, category, evidence_level, confidence_score, source_title, source_doi, similarity`

### `get_knowledge_context`
Get combined context for AI system prompt (text-based search).

```sql
SELECT * FROM get_knowledge_context(
  query_text := 'протеин для мышц',
  max_results := 5,
  min_evidence_level := 2
);
```

Returns: `context_text, knowledge_ids[], avg_evidence_level`

### `get_relevant_knowledge_for_query`
Get full knowledge records for UI display.

```sql
SELECT * FROM get_relevant_knowledge_for_query(
  query_text := 'сила и гипертрофия',
  max_results := 5,
  min_evidence_level := 2,
  filter_categories := ARRAY['strength', 'hypertrophy']  -- optional
);
```

### `save_message_knowledge`
Save knowledge usage for a chat message.

```sql
SELECT save_message_knowledge(
  p_message_id := 'uuid',
  p_knowledge_ids := ARRAY['uuid1', 'uuid2'],
  p_evidence_level := 3.5
);
```

### `get_pending_embeddings`
Get claims pending embedding generation (for KB Agent).

```sql
SELECT * FROM get_pending_embeddings(max_results := 10);
```

### `update_embedding_status`
Update embedding and status (for KB Agent).

```sql
SELECT update_embedding_status(
  p_claim_id := 'uuid',
  p_embedding := '[0.1, 0.2, ...]'::vector(1536),
  p_status := 'completed'  -- or 'failed'
);
```

## Automatic Embedding Generation

New claims automatically get `embedding_status = 'pending'` via trigger:

```sql
-- The auto_update_embedding trigger sets status on INSERT/UPDATE
INSERT INTO scientific_knowledge (claim, category, ...)
VALUES ('New claim', 'hypertrophy', ...);
-- embedding_status is automatically set to 'pending'
```

The KB Agent polls for pending claims and generates embeddings.

## Monitoring Knowledge Usage

Query to see which claims are most used:
```sql
SELECT 
  sk.claim,
  sk.category,
  COUNT(kf.id) as feedback_count
FROM scientific_knowledge sk
LEFT JOIN knowledge_feedback kf ON sk.id = ANY(kf.related_knowledge_ids)
GROUP BY sk.id
ORDER BY feedback_count DESC;
```

Query to check embedding generation status:
```sql
SELECT 
  embedding_status,
  COUNT(*) as count
FROM scientific_knowledge
GROUP BY embedding_status;
```

## Best Practices

1. **Cite sources** - Always include DOI when available
2. **Be conservative** - Lower confidence score if evidence is mixed
3. **Note limitations** - Every study has limitations
4. **Update regularly** - Science evolves, mark outdated claims as deprecated
5. **Test embeddings** - Verify semantic search finds your claim with relevant queries

## Troubleshooting

### Embeddings not found
- Run `python generate_embeddings.py --verify` to check coverage
- Ensure embeddings are 1536-dimensional (OpenAI text-embedding-3-small)

### Search returns irrelevant results
- Check embedding quality
- Adjust `match_threshold` in search (default 0.7, try 0.75-0.8)
- Verify claim text is clear and specific

### AI doesn't reference knowledge
- Check system prompt includes knowledge context
- Verify `buildEnhancedContext` is being called
- Ensure evidence level meets minimum threshold

## Resources

- [Supabase Vector Docs](https://supabase.com/docs/guides/ai)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Evidence-Based Practice Guidelines](https://www.cebm.ox.ac.uk/resources/ebm-tools)
