# BitHarbor API Reference

**Version:** v1  
**Base URL:** `/api/v1`  
**Authentication:** Bearer token (JWT) required for all endpoints except `/auth/setup` and `/auth/login`

---

## Table of Contents

- [Authentication](#authentication)
- [Participants](#participants)
- [Movies](#movies)
- [TV Shows](#tv-shows)
- [Music](#music)
- [Podcasts](#podcasts)
- [Videos](#videos)
- [Personal Media](#personal-media)
- [Schemas](#schemas)

---

## Authentication

### POST `/api/v1/auth/setup`

Bootstrap the system with an initial admin account.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "securePassword123",
  "display_name": "Admin User",
  "participants": [
    {
      "handle": "john_viewer",
      "display_name": "John Doe",
      "email": "john@example.com",
      "role": "viewer"
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "admin": {
    "admin_id": "uuid-here",
    "email": "admin@example.com",
    "display_name": "Admin User"
  },
  "participants": [
    {
      "participant_id": "uuid-here",
      "handle": "john_viewer",
      "display_name": "John Doe",
      "email": "john@example.com",
      "role": "viewer",
      "preferences_json": null
    }
  ]
}
```

---

### POST `/api/v1/auth/login`

Authenticate and receive access token.

**Request:**
```json
{
  "email": "admin@example.com",
  "password": "securePassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "admin": {
    "admin_id": "uuid-here",
    "email": "admin@example.com",
    "display_name": "Admin User"
  },
  "participants": []
}
```

---

### GET `/api/v1/auth/me`

Get current authenticated admin details.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "admin": {
    "admin_id": "uuid-here",
    "email": "admin@example.com",
    "display_name": "Admin User"
  }
}
```

---

## Participants

### GET `/api/v1/admin/participants`

List all participants for the current admin.

**Response:** `200 OK`
```json
[
  {
    "participant_id": "uuid-here",
    "handle": "john_viewer",
    "display_name": "John Doe",
    "email": "john@example.com",
    "role": "viewer",
    "preferences_json": null
  }
]
```

---

### POST `/api/v1/admin/participants`

Create a new participant.

**Request:**
```json
{
  "handle": "jane_viewer",
  "display_name": "Jane Smith",
  "email": "jane@example.com",
  "role": "viewer",
  "preferences_json": null
}
```

**Response:** `201 Created`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Smith",
  "email": "jane@example.com",
  "role": "viewer",
  "preferences_json": null
}
```

---

### PATCH `/api/v1/admin/participants/{participant_id}`

Update participant details.

**Request:**
```json
{
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "admin",
  "preferences_json": "{\"theme\": \"dark\"}"
}
```

**Response:** `200 OK`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "admin",
  "preferences_json": "{\"theme\": \"dark\"}"
}
```

---

### POST `/api/v1/admin/participants/{participant_id}/assign`

Assign a role to a participant.

**Request:**
```json
{
  "role": "editor"
}
```

**Response:** `200 OK`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "editor",
  "preferences_json": null
}
```

---

### GET `/api/v1/participants/{participant_id}`

Get a specific participant's details.

**Response:** `200 OK`
```json
{
  "participant_id": "uuid-here",
  "handle": "jane_viewer",
  "display_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "editor",
  "preferences_json": null
}
```

---

## Movies

Type-specific endpoints for movies. All endpoints require authentication.

### POST `/api/v1/movies/search`

Vector search across movie library only.

**Request:**
```json
{
  "query": "sci-fi action with time travel",
  "k": 10
}
```

**Response:** `200 OK`
```json
{
  "results": [
    {
      "media_id": "uuid-here",
      "score": 0.94,
      "type": "movie",
      "title": "The Matrix",
      "preview_url": "/api/v1/movies/media/uuid-here/stream"
    }
  ]
}
```

---

### GET `/api/v1/movies/media`

List all movie media items.

**Query Parameters:**
- `limit` (default: 20, max: 100)
- `offset` (default: 0)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "media_id": "uuid-here",
      "type": "movie",
      "title": "The Matrix",
      "source_type": "catalog",
      "vector_hash": "hash-here"
    }
  ],
  "total": 1
}
```

---

### GET `/api/v1/movies/media/{media_id}`

Get detailed movie metadata including TMDb enrichment.

**Response:** `200 OK` - Same format as general media detail with `enriched_metadata.movie` populated.

---

### GET `/api/v1/movies/media/{media_id}/stream`

Stream the movie file.

---

### POST `/api/v1/movies/ingest/start`

Ingest a movie file.

**Request:**
```json
{
  "path": "/mnt/media/movies/matrix.mp4",
  "metadata": {
    "title": "The Matrix",
    "year": 1999
  },
  "poster_path": "/mnt/posters/matrix.jpg"
}
```
*Note: `media_type` is automatically set to `"movie"`*

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "file_hash": "sha256-hash",
  "vector_hash": "embedding-hash"
}
```

---

### GET `/api/v1/movies/catalog/search`

Search TMDb and Internet Archive for catalog matches.

**Query Parameters:**
- `query` (required): Movie title to search for
- `limit` (default: 10, max: 50): Maximum number of results
- `year` (optional): Restrict matches to a specific release year

**Response:** `200 OK`
```json
{
  "matches": [
    {
      "match_key": "unique-match-key",
      "tmdb_id": 603,
      "tmdb_movie": {
        "title": "The Matrix",
        "overview": "Set in the 22nd century...",
        "release_date": "1999-03-31T00:00:00",
        "year": 1999,
        "runtime_min": 136,
        "genres": ["Action", "Science Fiction"],
        "vote_average": 8.2,
        "vote_count": 23000,
        "cast": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"]
      },
      "best_candidate": {
        "identifier": "the-matrix-1999",
        "score": 0.95,
        "downloads": 50000,
        "movie": {
          "title": "The Matrix",
          "year": 1999
        }
      },
      "candidates": []
    }
  ],
  "total": 1
}
```

---

### POST `/api/v1/movies/catalog/download`

Plan or execute a catalog-based download using a match key.

**Request:**
```json
{
  "match_key": "unique-match-key",
  "destination": "/mnt/downloads",
  "execute": true
}
```

**Query Parameters:**
- `match_key` (required): Match key obtained from catalog search
- `destination` (optional): Override destination directory
- `execute` (default: false): If true, perform the download; otherwise return plan

**Response:** `200 OK`
```json
{
  "match_key": "unique-match-key",
  "identifier": "the-matrix-1999",
  "title": "The Matrix",
  "destination": "/mnt/downloads",
  "video_file": "the-matrix-1999.mp4",
  "metadata_xml_file": "the-matrix-1999_meta.xml",
  "cover_art_file": "the-matrix-1999.jpg",
  "subtitle_files": ["the-matrix-1999_eng.srt"],
  "downloaded": true,
  "video_path": "/mnt/downloads/the-matrix-1999.mp4",
  "subtitle_paths": ["/mnt/downloads/the-matrix-1999_eng.srt"],
  "file_hash": "sha256-hash",
  "vector_hash": "embedding-hash",
  "vector_row_id": 123,
  "movie_id": 456,
  "created": true
}
```

---

## TV Shows

Type-specific endpoints for TV episodes.

### POST `/api/v1/tv/search`

Vector search across TV library only.

**Request:**
```json
{
  "query": "crime drama with meth",
  "k": 10
}
```

**Response:** `200 OK` - Same format as movie search with `type: "tv"`.

---

### GET `/api/v1/tv/media`

List all TV episode media items.

**Query Parameters:**
- `limit` (default: 20, max: 100)
- `offset` (default: 0)

**Response:** `200 OK`
```json
{
  "items": [
    {
      "media_id": "uuid-here",
      "type": "tv",
      "title": "Breaking Bad - S01E01",
      "source_type": "catalog",
      "vector_hash": "hash-here"
    }
  ],
  "total": 1
}
```

---

### GET `/api/v1/tv/media/{media_id}`

Get detailed TV episode metadata including TMDb enrichment.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "tv",
  "title": "Breaking Bad - S01E01",
  "source_type": "catalog",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 2880,
    "format": "mp4"
  },
  "enriched_metadata": {
    "tv_show": {
      "tmdb_id": 1396,
      "imdb_id": "tt0903747",
      "name": "Breaking Bad",
      "overview": "A high school chemistry teacher...",
      "first_air_date": "2008-01-20T00:00:00",
      "number_of_seasons": 5,
      "number_of_episodes": 62,
      "genres": ["Drama", "Crime"],
      "vote_average": 9.0
    },
    "tv_episode": {
      "tmdb_id": 62085,
      "series_name": "Breaking Bad",
      "series_tmdb_id": 1396,
      "name": "Pilot",
      "season_number": 1,
      "episode_number": 1,
      "air_date": "2008-01-20T00:00:00",
      "runtime_min": 58,
      "vote_average": 8.2
    }
  }
}
```

---

### GET `/api/v1/tv/media/{media_id}/stream`

Stream the TV episode file.

---

### POST `/api/v1/tv/ingest/start`

Ingest a TV episode file.

**Request:**
```json
{
  "path": "/mnt/media/tv/breaking_bad_s01e01.mp4",
  "metadata": {
    "title": "Breaking Bad",
    "season": 1,
    "episode": 1
  }
}
```
*Note: `media_type` is automatically set to `"tv"`*

**Response:** `200 OK` - Same format as movie ingest.

---

## Music

Type-specific endpoints for music tracks.

### POST `/api/v1/music/search`

Vector search across music library only.

**Request:**
```json
{
  "query": "upbeat electronic dance",
  "k": 10
}
```

**Response:** `200 OK` - Same format as movie search with `type: "music"`.

---

### GET `/api/v1/music/media`

List all music track media items.

---

### GET `/api/v1/music/media/{media_id}`

Get detailed music track metadata.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "music",
  "title": "Song Title - Artist Name",
  "source_type": "catalog",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 240,
    "format": "mp3",
    "bitrate": 320000
  },
  "enriched_metadata": {
    "music": {
      "title": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "track_number": 3,
      "year": 2020,
      "genres": ["Electronic", "Dance"]
    }
  }
}
```

---

### GET `/api/v1/music/media/{media_id}/stream`

Stream the music track file.

---

### POST `/api/v1/music/ingest/start`

Ingest a music track file.

**Request:**
```json
{
  "path": "/mnt/media/music/artist/album/track.mp3",
  "metadata": {
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name"
  }
}
```
*Note: `media_type` is automatically set to `"music"`*

---

## Podcasts

Type-specific endpoints for podcast episodes.

### POST `/api/v1/podcasts/search`

Vector search across podcast library only.

---

### GET `/api/v1/podcasts/media`

List all podcast episode media items.

---

### GET `/api/v1/podcasts/media/{media_id}`

Get detailed podcast episode metadata.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "podcast",
  "title": "Episode Title - Show Name",
  "source_type": "catalog",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 3600,
    "format": "mp3"
  },
  "enriched_metadata": {
    "podcast": {
      "title": "Episode Title",
      "show_name": "Show Name",
      "description": "Episode description...",
      "pub_date": "2024-01-15T00:00:00",
      "duration_s": 3600
    }
  }
}
```

---

### GET `/api/v1/podcasts/media/{media_id}/stream`

Stream the podcast episode file.

---

### POST `/api/v1/podcasts/ingest/start`

Ingest a podcast episode file.

---

## Videos

Type-specific endpoints for online videos (YouTube, etc.).

### POST `/api/v1/videos/search`

Vector search across online video library only.

---

### GET `/api/v1/videos/media`

List all online video media items.

---

### GET `/api/v1/videos/media/{media_id}`

Get detailed online video metadata.

---

### GET `/api/v1/videos/media/{media_id}/stream`

Stream the online video file.

---

### POST `/api/v1/videos/ingest/start`

Ingest an online video file.

---

## Personal Media

Type-specific endpoints for personal/home videos.

### POST `/api/v1/personal/search`

Vector search across personal media library only.

---

### GET `/api/v1/personal/media`

List all personal media items.

---

### GET `/api/v1/personal/media/{media_id}`

Get detailed personal media metadata.

**Response:** `200 OK`
```json
{
  "media_id": "uuid-here",
  "type": "personal",
  "title": "Family Vacation 2024",
  "source_type": "home",
  "vector_hash": "hash-here",
  "file_hash": "sha256-hash",
  "metadata": {
    "duration": 1200,
    "format": "mp4",
    "created_at": "2024-07-15T00:00:00"
  },
  "enriched_metadata": null
}
```

---

### GET `/api/v1/personal/media/{media_id}/stream`

Stream the personal media file.

---

### POST `/api/v1/personal/ingest/start`

Ingest a personal media file.

**Request:**
```json
{
  "path": "/mnt/home_videos/vacation_2024.mp4",
  "source_type": "home",
  "metadata": {
    "title": "Family Vacation 2024"
  }
}
```
*Note: `media_type` is automatically set to `"personal"`*

---

## Schemas

### MediaListResponse

```typescript
interface MediaListResponse {
  items: MediaSummary[];
  total: number;
}
```

### MediaSummary

```typescript
interface MediaSummary {
  media_id: string;
  type: MediaType;
  title: string | null;
  source_type: SourceType;
  vector_hash: string;
}
```

### MediaDetail

Extends MediaSummary with additional fields:

```typescript
interface MediaDetail extends MediaSummary {
  file_hash: string;
  metadata: Record<string, any> | null;
  enriched_metadata: EnrichedMetadata | null;
}
```

### ImageMetadata

```typescript
interface ImageMetadata {
  file_path: string;
  width: number | null;
  height: number | null;
  aspect_ratio: number | null;
}
```

### MovieMedia

```typescript
interface MovieMedia {
  // Basic Info
  title: string;
  tagline: string | null;
  overview: string | null;
  
  // Release Info
  release_date: string | null;  // ISO 8601
  year: number | null;
  
  // Runtime & Production
  runtime_min: number | null;
  
  // Categories
  genres: string[] | null;
  languages: string[] | null;
  
  // Ratings
  vote_average: number | null;  // 0-10
  vote_count: number | null;
  
  // People
  cast: string[] | null;  // Top cast members
  
  // Flags & Metadata
  rating: string | null;
  file_hash: string | null;
  embedding_hash: string | null;
  path: string | null;
  format: string | null;
  media_type: string | null;
  catalog_source: string | null;
  catalog_id: string | null;
  catalog_score: number | null;
  catalog_downloads: number | null;
  poster: ImageMetadata | null;
  backdrop: ImageMetadata | null;
}
```

### TvShowMedia

```typescript
interface TvShowMedia {
  // Basic Info
  name: string;
  overview: string | null;
  type: string | null;  // Scripted, Reality, etc.
  status: string | null;  // Returning, Ended, etc.
  
  // Air Dates
  first_air_date: string | null;  // ISO 8601
  last_air_date: string | null;  // ISO 8601
  
  // Episodes & Seasons
  number_of_seasons: number | null;
  number_of_episodes: number | null;
  
  // Categories
  genres: string[] | null;
  languages: string[] | null;
  
  // Ratings
  vote_average: number | null;  // 0-10
  vote_count: number | null;
  
  // People
  cast: string[] | null;
  
  // Metadata
  file_hash: string | null;
  embedding_hash: string | null;
  path: string | null;
  format: string | null;
  media_type: string | null;
  catalog_source: string | null;
  catalog_id: string | null;
  poster: ImageMetadata | null;
  backdrop: ImageMetadata | null;
  
  seasons: TvSeasonMetadata[] | null;
}
```

### TvSeasonMetadata

```typescript
interface TvSeasonMetadata {
  name: string;
  overview: string | null;
  season_number: number;
  episodes: TvEpisodeMetadata[] | null;
}
```

### TvEpisodeMetadata

```typescript
interface TvEpisodeMetadata {
  name: string;
  overview: string | null;
  episode_number: number;
  air_date: string | null;  // ISO 8601
  runtime_min: number | null;
}
```

### MusicTrackMedia

```typescript
interface MusicTrackMedia {
  title: string;
  track_number: number | null;
  duration_s: number | null;
  
  // Metadata
  file_hash: string | null;
  embedding_hash: string | null;
  path: string | null;
  format: string | null;
  media_type: string | null;
  catalog_source: string | null;
  catalog_id: string | null;
}
```

### PodcastEpisodeMedia

```typescript
interface PodcastEpisodeMedia {
  // Show Info
  podcast_title: string;
  publisher: string | null;
  description: string | null;
  
  // Episode Info
  episode_title: string;
  pub_date: string | null;  // ISO 8601
  duration_s: number | null;
  episode_description: string | null;
  
  // Metadata
  file_hash: string | null;
  embedding_hash: string | null;
  path: string | null;
  format: string | null;
  media_type: string | null;
  poster: ImageMetadata | null;
}
```

### PersonalMedia

```typescript
interface PersonalMedia {
  title: string | null;
  
  // Metadata
  file_hash: string | null;
  embedding_hash: string | null;
  path: string | null;
  format: string | null;
  media_type: string | null;
}
```

### CatalogMatch

```typescript
interface CatalogMatch {
  match_key: string;  // Key used to retrieve the stored match
  tmdb_id: number;
  tmdb_movie: MovieMedia;
  best_candidate: CatalogMatchCandidate;
  candidates: CatalogMatchCandidate[];
}
```

### CatalogMatchCandidate

```typescript
interface CatalogMatchCandidate {
  identifier: string;  // Internet Archive identifier
  score: number;  // 0.0 to 1.0
  downloads: number | null;
  movie: MovieMedia;
}
```

### CatalogMatchResponse

```typescript
interface CatalogMatchResponse {
  matches: CatalogMatch[];
  total: number;
}
```

### CatalogDownloadRequest

```typescript
interface CatalogDownloadRequest {
  match_key: string;  // Match key obtained from catalog search
  destination?: string | null;  // Override destination directory
  execute?: boolean;  // Default: false
}
```

### CatalogDownloadResponse

```typescript
interface CatalogDownloadResponse {
  match_key: string;
  identifier: string;
  title: string | null;
  destination: string | null;
  video_file: string | null;
  metadata_xml_file: string | null;
  cover_art_file: string | null;
  subtitle_files: string[];
  downloaded: boolean;
  video_path: string | null;
  subtitle_paths: string[];
  file_hash: string | null;
  vector_hash: string | null;
  vector_row_id: number | null;
  movie_id: number | null;
  created: boolean | null;
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 404 Not Found

```json
{
  "detail": "Media not found"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## Notes

1. **Authentication**: All endpoints except `/auth/setup` and `/auth/login` require a valid JWT token in the `Authorization` header.

2. **Pagination**: List endpoints support `limit` and `offset` query parameters for pagination.

3. **Type-Specific Routes**: Each media type has its own set of routes under `/movies`, `/tv`, `/music`, `/podcasts`, `/videos`, and `/personal`. These provide type-specific functionality and automatically filter results to the appropriate media type.

4. **Movie Catalog Integration**: The `/movies/catalog/search` and `/movies/catalog/download` endpoints integrate with TMDb and Internet Archive to search and download catalog movies with automatic metadata enrichment.

5. **Vector Search**: Search endpoints use embedding-based similarity search for natural language queries across media libraries.

6. **Streaming**: Stream endpoints return `FileResponse` objects with appropriate `Content-Type` headers and support HTTP range requests for efficient streaming.

7. **Enrichment**: Movie and TV content can be enriched with TMDb metadata. Music and podcast enrichment schemas are defined for future implementation.

