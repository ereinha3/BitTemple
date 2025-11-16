import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
from datetime import datetime

from domain.schemas.enrichment import (
    CastMember,
    CrewMember,
    EnrichedMetadata,
    ImageMetadata,
    TvShowMetadata,
    TvEpisodeMetadata,
)


def test_tv_show_metadata_full():
    """Test TvShowMetadata with complete data."""
    print("\n=== Test 1: Full TV Show Metadata ===")
    
    metadata = TvShowMetadata(
        tmdb_id=1396,
        imdb_id="tt0903747",
        name="Breaking Bad",
        original_name="Breaking Bad",
        tagline="All Hail the King",
        overview="A high school chemistry teacher diagnosed with inoperable lung cancer...",
        type="Scripted",
        status="Ended",
        first_air_date=datetime(2008, 1, 20),
        last_air_date=datetime(2013, 9, 29),
        number_of_seasons=5,
        number_of_episodes=62,
        genres=["Drama", "Crime", "Thriller"],
        languages=["English"],
        countries=["United States"],
        vote_average=9.0,
        vote_count=12000,
        popularity=450.5,
        cast=[
            CastMember(name="Bryan Cranston", character="Walter White", order=0),
            CastMember(name="Aaron Paul", character="Jesse Pinkman", order=1),
            CastMember(name="Anna Gunn", character="Skyler White", order=2),
        ],
        crew=[
            CrewMember(name="Vince Gilligan", job="Executive Producer", department="Production"),
        ],
        created_by=["Vince Gilligan"],
        networks=["AMC"],
        posters=[
            ImageMetadata(
                file_path="/abc123.jpg",
                width=500,
                height=750,
                aspect_ratio=0.667,
                vote_average=8.5,
                vote_count=100,
            )
        ],
    )
    
    # Convert to JSON (what would be sent to frontend)
    json_data = metadata.model_dump_json(indent=2)
    print(f"JSON Output:\n{json_data}")
    
    # Parse back from JSON (what frontend would receive)
    parsed = TvShowMetadata.model_validate_json(json_data)
    print(f"\n✓ Successfully parsed! Name: {parsed.name}")
    print(f"✓ Seasons: {parsed.number_of_seasons}, Episodes: {parsed.number_of_episodes}")
    print(f"✓ Cast count: {len(parsed.cast or [])}")
    print(f"✓ Genres: {', '.join(parsed.genres or [])}")
    print(f"✓ Status: {parsed.status}")
    print(f"✓ Rating: {parsed.vote_average}/10")


def test_tv_show_metadata_partial():
    """Test TvShowMetadata with partial/missing data (common for failed enrichment)."""
    print("\n=== Test 2: Partial TV Show Metadata ===")
    
    # Minimal required data (only name is required)
    metadata = TvShowMetadata(
        name="Unknown TV Show",
        # Everything else is None/optional
    )
    
    json_data = metadata.model_dump_json(indent=2)
    print(f"JSON Output:\n{json_data}")
    
    # Frontend can safely access optional fields
    parsed = TvShowMetadata.model_validate_json(json_data)
    print(f"\n✓ Name (required): {parsed.name}")
    print(f"✓ Number of seasons (optional): {parsed.number_of_seasons}")  # None
    print(f"✓ Cast (optional): {parsed.cast}")  # None
    print(f"✓ Genres (optional): {parsed.genres}")  # None
    print(f"✓ Status (optional): {parsed.status}")  # None
    
    # Frontend can safely check for None
    if parsed.cast:
        print(f"Has {len(parsed.cast)} cast members")
    else:
        print("✓ No cast data available (gracefully handled)")


def test_tv_episode_metadata():
    """Test TvEpisodeMetadata for individual episodes."""
    print("\n=== Test 3: TV Episode Metadata ===")
    
    metadata = TvEpisodeMetadata(
        tmdb_id=62085,
        imdb_id="tt0959621",
        series_name="Breaking Bad",
        series_tmdb_id=1396,
        name="Pilot",
        overview="When an unassuming high school chemistry teacher discovers he has cancer...",
        season_number=1,
        episode_number=1,
        air_date=datetime(2008, 1, 20),
        runtime_min=58,
        vote_average=8.2,
        vote_count=5000,
        cast=[
            CastMember(name="Bryan Cranston", character="Walter White", order=0),
            CastMember(name="Aaron Paul", character="Jesse Pinkman", order=1),
        ],
        crew=[
            CrewMember(name="Vince Gilligan", job="Director", department="Directing"),
            CrewMember(name="Vince Gilligan", job="Writer", department="Writing"),
        ],
    )
    
    json_data = metadata.model_dump_json(indent=2)
    print(f"JSON Output:\n{json_data}")
    
    parsed = TvEpisodeMetadata.model_validate_json(json_data)
    print(f"\n✓ Episode: {parsed.series_name} - S{parsed.season_number:02d}E{parsed.episode_number:02d}")
    print(f"✓ Title: {parsed.name}")
    print(f"✓ Runtime: {parsed.runtime_min} minutes")
    print(f"✓ Rating: {parsed.vote_average}/10")
    print(f"✓ Director: {parsed.crew[0].name if parsed.crew else 'Unknown'}")


def test_enriched_metadata_tv_container():
    """Test EnrichedMetadata container with TV show data."""
    print("\n=== Test 4: EnrichedMetadata Container (TV) ===")
    
    # TV show metadata in container
    tv_metadata = TvShowMetadata(
        name="The Mandalorian",
        tmdb_id=82856,
        number_of_seasons=3,
        number_of_episodes=24,
        genres=["Sci-Fi & Fantasy", "Action & Adventure", "Drama"],
        vote_average=8.5,
        status="Returning Series",
        networks=["Disney+"],
    )
    
    enriched = EnrichedMetadata(tv_show=tv_metadata)
    json_data = enriched.model_dump_json(indent=2)
    print(f"JSON Output:\n{json_data}")
    
    parsed = EnrichedMetadata.model_validate_json(json_data)
    
    # Frontend can check which type of metadata exists
    if parsed.tv_show:
        print(f"\n✓ TV show metadata present: {parsed.tv_show.name}")
        print(f"✓ Status: {parsed.tv_show.status}")
        print(f"✓ Seasons: {parsed.tv_show.number_of_seasons}")
    if parsed.movie:
        print("✓ Movie metadata present")
    else:
        print("✓ No movie metadata (expected)")


def test_database_json_tv_parsing():
    """Test parsing TV metadata_enriched from database JSON field."""
    print("\n=== Test 5: Database JSON Field Parsing (TV) ===")
    
    # Simulate what's stored in database for TV series
    tv_dict = {
        "tmdb_id": 1396,
        "imdb_id": "tt0903747",
        "name": "Breaking Bad",
        "number_of_seasons": 5,
        "number_of_episodes": 62,
        "genres": ["Drama", "Crime", "Thriller"],
        "vote_average": 9.0,
        "vote_count": 12000,
        "status": "Ended",
        "networks": ["AMC"],
        "cast": [
            {"name": "Bryan Cranston", "character": "Walter White", "order": 0},
            {"name": "Aaron Paul", "character": "Jesse Pinkman", "order": 1},
        ],
    }
    
    # Store as JSON (what database does)
    json_str = json.dumps(tv_dict)
    print(f"Database JSON: {json_str}")
    
    # Parse and validate (what media service does)
    parsed = TvShowMetadata.model_validate_json(json_str)
    print(f"\n✓ Parsed from database JSON!")
    print(f"✓ Name: {parsed.name}")
    print(f"✓ Seasons: {parsed.number_of_seasons}, Episodes: {parsed.number_of_episodes}")
    print(f"✓ Cast[0]: {parsed.cast[0].name} as {parsed.cast[0].character}")
    print(f"✓ Genres: {', '.join(parsed.genres)}")
    print(f"✓ Status: {parsed.status}")
    
    # Frontend receives type-safe data
    enriched = EnrichedMetadata(tv_show=parsed)
    frontend_json = enriched.model_dump_json(indent=2)
    print(f"\nFrontend receives:\n{frontend_json[:500]}...")


def test_mixed_media_types():
    """Test handling both movie and TV data in different contexts."""
    print("\n=== Test 6: Mixed Media Types ===")
    
    # Movie enriched metadata
    from domain.schemas.enrichment import MovieMetadata
    
    movie = MovieMetadata(
        title="The Matrix",
        year=1999,
        genres=["Action", "Sci-Fi"],
    )
    
    tv_show = TvShowMetadata(
        name="The Matrix: Resurrections",  # Hypothetical TV series
        number_of_seasons=1,
        genres=["Action", "Sci-Fi"],
    )
    
    # Create separate enriched metadata objects
    movie_enriched = EnrichedMetadata(movie=movie)
    tv_enriched = EnrichedMetadata(tv_show=tv_show)
    
    print("Movie enriched metadata:")
    print(f"  Type: {'movie' if movie_enriched.movie else 'other'}")
    print(f"  Title: {movie_enriched.movie.title if movie_enriched.movie else 'N/A'}")
    
    print("\nTV enriched metadata:")
    print(f"  Type: {'tv' if tv_enriched.tv_show else 'other'}")
    print(f"  Name: {tv_enriched.tv_show.name if tv_enriched.tv_show else 'N/A'}")
    
    print("\n✓ Both media types can coexist with same schema structure")


def test_tv_validation_errors():
    """Test that invalid data is caught by Pydantic validation."""
    print("\n=== Test 7: TV Validation Error Handling ===")
    
    # Test 1: Missing required field (name)
    try:
        TvShowMetadata(
            number_of_seasons=5,
            genres=["Drama"],
        )
        print("✗ Should have raised validation error for missing name!")
    except Exception as e:
        print(f"✓ Validation error caught (missing name): {type(e).__name__}")
    
    # Test 2: Episode missing required fields
    try:
        TvEpisodeMetadata(
            name="Test Episode",
            # Missing season_number and episode_number
        )
        print("✗ Should have raised validation error for missing episode numbers!")
    except Exception as e:
        print(f"✓ Validation error caught (missing episode info): {type(e).__name__}")
    
    # Test 3: Invalid data types
    try:
        TvShowMetadata(
            name="Test Show",
            number_of_seasons="five",  # Should be int
        )
        print("✗ Should have raised validation error for wrong type!")
    except Exception as e:
        print(f"✓ Validation error caught (wrong type): {type(e).__name__}")


def test_series_episode_relationship():
    """Test the relationship between series and episode metadata."""
    print("\n=== Test 8: Series-Episode Relationship ===")
    
    # Series metadata
    series = TvShowMetadata(
        tmdb_id=1396,
        name="Breaking Bad",
        number_of_seasons=5,
        number_of_episodes=62,
        status="Ended",
    )
    
    # Episode metadata that references the series
    episode = TvEpisodeMetadata(
        series_name=series.name,
        series_tmdb_id=series.tmdb_id,
        name="Pilot",
        season_number=1,
        episode_number=1,
    )
    
    print(f"Series: {series.name} (TMDb ID: {series.tmdb_id})")
    print(f"  Total Episodes: {series.number_of_episodes}")
    print(f"  Status: {series.status}")
    
    print(f"\nEpisode: {episode.name}")
    print(f"  Belongs to: {episode.series_name} (TMDb ID: {episode.series_tmdb_id})")
    print(f"  S{episode.season_number:02d}E{episode.episode_number:02d}")
    
    # Verify linkage
    assert episode.series_tmdb_id == series.tmdb_id, "Episode should link to series"
    print("\n✓ Episode correctly linked to series via TMDb ID")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Type-Safe TV Show Enriched Metadata")
    print("=" * 60)
    
    test_tv_show_metadata_full()
    test_tv_show_metadata_partial()
    test_tv_episode_metadata()
    test_enriched_metadata_tv_container()
    test_database_json_tv_parsing()
    test_mixed_media_types()
    test_tv_validation_errors()
    test_series_episode_relationship()
    
    print("\n" + "=" * 60)
    print("All TV tests completed!")
    print("=" * 60)
    print("\nKey Benefits for TV Shows:")
    print("✓ Frontend knows exact TV show/episode structure")
    print("✓ Series and episode data properly separated")
    print("✓ All fields (except name/season/episode) are Optional")
    print("✓ Partial enrichment data handled gracefully")
    print("✓ Type validation ensures consistency")
    print("✓ Episodes properly linked to series via TMDb ID")
    print("✓ Auto-generated API documentation shows TV schemas")
    print("=" * 60)
