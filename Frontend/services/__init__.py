"""Frontend Service Layer for Campus Sustainability Dashboard.

Provides clean domain abstraction over Supabase persistence and the
ML operational WasteStatusEngine. Keeps UI components free of database logic
and structured for straightforward migration behind FastAPI in the future.
"""
