"""
Integration tests for the complete poker analysis workflow.

Tests the full pipeline:
1. Upload hand history file
2. Parse hands
3. Insert into database
4. Calculate player statistics
5. Query player data
6. Claude AI integration
"""

import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.models import PlayerStats, RawHand, HandAction, PlayerHandSummary, UploadSession

# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    """Create test database for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client for FastAPI"""
    return TestClient(app)


@pytest.fixture
def sample_hand_file():
    """Path to sample hand history file"""
    return Path(__file__).parent / "data" / "sample_hands.txt"


class TestCompleteWorkflow:
    """Test complete end-to-end workflow"""

    def test_health_check(self, client, test_db):
        """Test API health check"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "database" in data

    def test_database_stats_empty(self, client, test_db):
        """Test database stats with empty database"""
        response = client.get("/api/database/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_hands"] == 0
        assert data["total_players"] == 0

    def test_upload_hand_history(self, client, test_db, sample_hand_file):
        """Test complete upload workflow"""
        if not sample_hand_file.exists():
            pytest.skip("Sample hand file not found")

        with open(sample_hand_file, "rb") as f:
            response = client.post(
                "/api/upload",
                files={"file": ("test_hands.txt", f, "text/plain")}
            )

        assert response.status_code == 201
        data = response.json()

        # Check response structure
        assert "session_id" in data
        assert "hands_parsed" in data
        assert "players_updated" in data
        assert data["hands_parsed"] > 0
        assert data["players_updated"] > 0

    def test_players_list_after_upload(self, client, test_db, sample_hand_file):
        """Test player list after uploading hands"""
        if not sample_hand_file.exists():
            pytest.skip("Sample hand file not found")

        # Upload file first
        with open(sample_hand_file, "rb") as f:
            upload_response = client.post(
                "/api/upload",
                files={"file": ("test_hands.txt", f, "text/plain")}
            )
        assert upload_response.status_code == 201

        # Get players list
        response = client.get("/api/players?min_hands=1")
        assert response.status_code == 200
        players = response.json()
        assert len(players) > 0

        # Check player structure
        player = players[0]
        assert "player_name" in player
        assert "total_hands" in player

    def test_player_profile(self, client, test_db, sample_hand_file):
        """Test player profile retrieval"""
        if not sample_hand_file.exists():
            pytest.skip("Sample hand file not found")

        # Upload file first
        with open(sample_hand_file, "rb") as f:
            upload_response = client.post(
                "/api/upload",
                files={"file": ("test_hands.txt", f, "text/plain")}
            )
        assert upload_response.status_code == 201

        # Get players
        players_response = client.get("/api/players?min_hands=1")
        players = players_response.json()
        assert len(players) > 0

        # Get first player's profile
        player_name = players[0]["player_name"]
        response = client.get(f"/api/players/{player_name}")
        assert response.status_code == 200

        profile = response.json()
        assert profile["player_name"] == player_name
        assert "total_hands" in profile
        assert "vpip_pct" in profile
        assert "pfr_pct" in profile
        assert "exploitability_index" in profile

    def test_database_stats_after_upload(self, client, test_db, sample_hand_file):
        """Test database stats after upload"""
        if not sample_hand_file.exists():
            pytest.skip("Sample hand file not found")

        # Upload file
        with open(sample_hand_file, "rb") as f:
            client.post(
                "/api/upload",
                files={"file": ("test_hands.txt", f, "text/plain")}
            )

        # Check stats
        response = client.get("/api/database/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_hands"] > 0
        assert data["total_players"] > 0

    def test_invalid_file_upload(self, client, test_db):
        """Test uploading invalid file type"""
        response = client.post(
            "/api/upload",
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        )
        assert response.status_code == 400

    def test_player_not_found(self, client, test_db):
        """Test querying non-existent player"""
        response = client.get("/api/players/NonExistentPlayer123")
        assert response.status_code == 404

    def test_database_schema(self, client, test_db):
        """Test database schema endpoint"""
        response = client.get("/api/database/schema")
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "raw_hands" in data["tables"]
        assert "player_stats" in data["tables"]


class TestClaudeIntegration:
    """Test Claude AI integration"""

    def test_claude_query_endpoint(self, client, test_db):
        """Test Claude query endpoint structure"""
        # Note: This will fail if ANTHROPIC_API_KEY is not set
        # In production, skip if key not available
        response = client.post(
            "/api/query/claude",
            json={
                "query": "Who are the most exploitable players?"
            }
        )

        # Should return 200 even if Claude fails (graceful error handling)
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "response" in data

    def test_claude_query_with_history(self, client, test_db):
        """Test Claude query with conversation history"""
        response = client.post(
            "/api/query/claude",
            json={
                "query": "Tell me more about that player",
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "Who is the most exploitable player?"
                    },
                    {
                        "role": "assistant",
                        "content": "Based on the data, Player123 has an exploitability index of 75."
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data


class TestDataIntegrity:
    """Test data integrity and consistency"""

    def test_player_stats_consistency(self, client, test_db, sample_hand_file):
        """Test that player stats are consistent after upload"""
        if not sample_hand_file.exists():
            pytest.skip("Sample hand file not found")

        # Upload file
        with open(sample_hand_file, "rb") as f:
            upload_response = client.post(
                "/api/upload",
                files={"file": ("test_hands.txt", f, "text/plain")}
            )

        players_updated = upload_response.json()["players_updated"]

        # Get player count
        players_response = client.get("/api/players?min_hands=0")
        player_count = len(players_response.json())

        # Should match
        assert players_updated == player_count

    def test_composite_metrics_calculated(self, client, test_db, sample_hand_file):
        """Test that composite metrics are calculated"""
        if not sample_hand_file.exists():
            pytest.skip("Sample hand file not found")

        # Upload file
        with open(sample_hand_file, "rb") as f:
            client.post(
                "/api/upload",
                files={"file": ("test_hands.txt", f, "text/plain")}
            )

        # Get a player profile
        players_response = client.get("/api/players?min_hands=50")
        players = players_response.json()

        if len(players) > 0:
            player_name = players[0]["player_name"]
            profile_response = client.get(f"/api/players/{player_name}")
            profile = profile_response.json()

            # Check that composite metrics exist (may be None if insufficient data)
            assert "exploitability_index" in profile
            assert "pressure_vulnerability_score" in profile
            assert "player_type" in profile


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_empty_file_upload(self, client, test_db):
        """Test uploading empty file"""
        response = client.post(
            "/api/upload",
            files={"file": ("empty.txt", b"", "text/plain")}
        )
        # Should handle gracefully
        assert response.status_code in [400, 500]

    def test_malformed_hand_history(self, client, test_db):
        """Test uploading malformed hand history"""
        malformed_content = b"This is not a valid hand history\nJust random text"
        response = client.post(
            "/api/upload",
            files={"file": ("malformed.txt", malformed_content, "text/plain")}
        )
        # Should handle gracefully
        assert response.status_code in [400, 500]

    def test_player_filtering(self, client, test_db):
        """Test player filtering with various parameters"""
        # Should not crash with extreme values
        response = client.get("/api/players?min_hands=999999")
        assert response.status_code == 200

        response = client.get("/api/players?min_hands=0&limit=1000")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
