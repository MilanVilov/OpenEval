"""Compatibility module for deployments importing ``app.main``."""

from fastapi import FastAPI

from app import app, create_app

__all__ = ["FastAPI", "app", "create_app"]
