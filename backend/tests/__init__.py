"""Test suite package for backend controllers.

Importing this package redirects the backend database engine to a throwaway file.
Test ``setUp`` methods delete rows from ``settings``, ``machines`` and ``devices``, so
binding to the real ``codes.db`` would destroy the operator's runtime configuration.
"""

from backend.tests._isolation import use_throwaway_database

use_throwaway_database()
