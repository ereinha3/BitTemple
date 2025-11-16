# Catalog Service Features

## Overview
The catalog service enables searching and ingesting public domain movies from Internet Archive into BitHarbor with automatic TMDb enrichment.

## Key Features

### 1. Intelligent Search with Deduplication

**Problem:** Internet Archive often has multiple versions of the same movie with varying quality and metadata.

**Solution:** Implemented a ranking system that:
- **Deduplicates** results by (title, year) combination
- **Ranks** versions using a scoring algorithm:
  - `score = (downloads / 10000) + (avg_rating × 2)`
  - Higher downloads = more popular version
  - Higher rating = better quality
- **Prioritizes** the best version when multiple exist

**API Endpoint:** `POST /api/v1/catalog/search/internet-archive`

**Example Request:**
```json
{
  "query": "Metropolis",
  "rows": 20,
  "sorts": ["downloads desc", "avg_rating desc"],
  "filters": ["language:eng"]
}
```

**Example Response:**
```json
{
  "results": [
    {
      "identifier": "metropolis_1927",
      "title": "Metropolis",
      "year": "1927",
      "description": "Classic German expressionist sci-fi film...",
      "downloads": 125000,
      "item_size": 1024000000,
      "avg_rating": 4.5,
      "num_reviews": 234
    }
  ],
  "total": 1
}
```

**New Fields:**
- `avg_rating`: Average user rating (0-5 stars)
- `num_reviews`: Number of user reviews
- `score`: Calculated ranking score (property)

### 2. Search-Enhanced TMDb Matching

**Problem:** Internet Archive metadata may be incomplete or formatted inconsistently, leading to poor TMDb matches.

**Solution:** Allow passing search metadata (title, year) during ingestion for better TMDb lookups.

**Workflow:**
1. User searches Internet Archive
2. Gets clean, structured results with title and year
3. When ingesting, passes this metadata along
4. TMDb enrichment uses the search metadata as the primary source
5. Falls back to Internet Archive metadata if search data not provided

**API Endpoint:** `POST /api/v1/catalog/ingest/internet-archive`

**Example Request (with search metadata):**
```json
{
  "identifier": "fantastic-planet__1973",
  "title": "Fantastic Planet",
  "year": 1973,
  "cleanup_after_ingest": true,
  "include_subtitles": true
}
```

**Benefits:**
- More accurate TMDb matches
- Better movie metadata (cast, crew, ratings)
- Improved poster art from TMDb
- Consistent year formatting

### 3. Complete Ingestion Pipeline

The catalog service orchestrates a 6-step pipeline:

1. **Download** from Internet Archive
   - Video file (MP4, MKV, etc.)
   - Cover art/poster
   - Metadata XML
   - Subtitles (optional)

2. **Extract Metadata** from Internet Archive
   - Title, year, description
   - Director/creator
   - Runtime
   - Languages

3. **Override with Search Metadata** (if provided)
   - Use cleaner title from search
   - Use normalized year from search

4. **Build Ingest Request**
   - Path to video file
   - Media type (movie)
   - Source type (catalog)
   - Metadata dictionary
   - Poster path

5. **Ingest into BitHarbor**
   - Store video in content-addressed storage
   - Generate BLAKE3 file hash
   - Enrich with TMDb (cast, crew, ratings, genres)
   - Generate ImageBind embeddings (1024-dim vector)
   - Add to DiskANN vector index

6. **Cleanup** (optional)
   - Delete downloaded files after successful ingest
   - Saves disk space on temporary storage

## Usage Example

### Search for a Movie
```python
# POST /api/v1/catalog/search/internet-archive
{
  "query": "Night of the Living Dead",
  "rows": 10,
  "sorts": ["downloads desc", "avg_rating desc"],
  "filters": ["language:eng"]
}
```

### Ingest the Best Version
```python
# POST /api/v1/catalog/ingest/internet-archive
{
  "identifier": "night_of_the_living_dead",
  "title": "Night of the Living Dead",  # From search results
  "year": 1968,  # From search results
  "cleanup_after_ingest": true
}
```

### Result
The movie is now:
- ✅ Stored in content-addressed storage
- ✅ Enriched with TMDb metadata
- ✅ Indexed with ImageBind embeddings
- ✅ Searchable via semantic search
- ✅ Available in the BitHarbor web interface

## Technical Details

### Duplicate Detection Algorithm
```python
# Group by (title, year)
seen_titles: dict[tuple[str, str], CatalogSearchResult] = {}

# Calculate score for ranking
score = (downloads / 10000) + (avg_rating × 2)

# Keep only the highest-scoring version
if score > existing_score:
    seen_titles[key] = new_result
```

### TMDb Matching Priority
1. **Search metadata** (title, year) - most reliable
2. **Internet Archive metadata** (fallback)
3. **TMDb fuzzy search** (if exact match fails)

### Metadata Flow
```
Internet Archive Search
    ↓
Clean, structured metadata (title, year, rating)
    ↓
Ingest endpoint (passes metadata)
    ↓
Catalog service (overrides IA metadata with search metadata)
    ↓
Ingest service (uses metadata for TMDb lookup)
    ↓
TMDb enrichment (finds correct movie)
    ↓
Complete movie details in BitHarbor
```

## Configuration

### Environment Variables
- `RAID_TMP_DIR`: Default download directory (default: `/tmp`)
- `TMDB_API_KEY`: TMDb API key for enrichment
- `TMDB_ACCESS_TOKEN`: TMDb access token

### Default Behavior
- **Sorts:** `["downloads desc", "avg_rating desc"]` (best first)
- **Deduplication:** Enabled by default
- **Cleanup:** Enabled by default
- **Subtitles:** Downloaded by default

## Future Enhancements

Potential improvements:
- [ ] Add configurable scoring weights (e.g., prefer ratings over downloads)
- [ ] Support for TV shows from Internet Archive
- [ ] Batch ingestion (multiple movies at once)
- [ ] Background job queue for long downloads
- [ ] Preview/thumbnail generation before full download
- [ ] User preferences for default sort order
