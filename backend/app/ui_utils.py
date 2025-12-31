"""UI utilities for template rendering and CSRF protection."""

import os
from fastapi.templating import Jinja2Templates
from app.services.csrf import csrf_service

# Get current file directory for absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Single instance of templates to be used across the application
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Register CSRF token function directly (no wrapper needed)
templates.env.globals["csrf_token"] = csrf_service.generate_token

