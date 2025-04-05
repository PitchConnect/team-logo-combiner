import pytest
import os
import sys
from flask import Flask

# Add the parent directory to sys.path to import app and team_logo_combiner
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as flask_app
import team_logo_combiner

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Set test configuration
    test_app = flask_app.app
    test_app.config.update({
        "TESTING": True,
    })
    
    # Return the app for testing
    yield test_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def test_assets_dir():
    """Path to test assets directory."""
    return os.path.join(os.path.dirname(__file__), 'test_assets')

@pytest.fixture(autouse=True)
def setup_test_assets(test_assets_dir):
    """Ensure test assets directory exists."""
    os.makedirs(test_assets_dir, exist_ok=True)
    # Create a test background image if needed
    yield
    # Cleanup if necessary
