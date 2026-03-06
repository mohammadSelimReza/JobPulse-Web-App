"""
Django development settings for Sahel project.
"""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# CORS — allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
