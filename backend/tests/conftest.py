"""Test isolation for the SQLite database (pytest entry point).

``backend.models`` resolves ``sqlite:///codes.db`` relative to the working directory,
so running the suite from the repository root used to destroy the developer's real
database -- including ``api_key``, which then no longer matched the kiosk's
``VITE_API_KEY``.

The environment variable must be set at import time, before any ``backend.*`` module is
imported, because the engine is created at module import. ``backend/tests/__init__.py``
does the same for the unittest entry point, and ``backend.models`` refuses outright to
bind to the real database while under test.
"""

from backend.tests._isolation import use_throwaway_database

use_throwaway_database()
