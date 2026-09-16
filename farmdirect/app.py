"""Vercel zero-configuration Flask entrypoint."""
from app_factory import create_app

app = create_app()
