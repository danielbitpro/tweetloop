"""
Authentication layer for TweetLoop.

Dual auth system:
  1. Supabase JWT (when SUPABASE_URL is set)
  2. Password from .env (when SUPABASE_URL is NOT set)

The @require_auth decorator handles both transparently.
"""

import os
from functools import wraps
from flask import request, jsonify, session

from typing import Any, Optional

from database import SUPABASE_URL, SUPABASE_SERVICE_KEY, get_supabase_client, get_user

# ---------------------------------------------------------------------------
# Password auth (self-hosted / offline mode)
# ---------------------------------------------------------------------------

def get_password():
    """Load password from .env file if it exists."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('PASSWORD='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    return os.environ.get('PASSWORD', '')

PASSWORD_HASH = get_password()
USE_PASSWORD_AUTH = bool(PASSWORD_HASH)

# ---------------------------------------------------------------------------
# Supabase JWT auth (cloud / local with Supabase)
# ---------------------------------------------------------------------------

def verify_supabase_jwt(token: str) -> dict:
    """
    Verify a Supabase JWT and return user info.
    
    Args:
        token: JWT token (without 'Bearer ' prefix)
        
    Returns:
        dict with user info, or None if invalid
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Verify the JWT and get user data
        user = client.auth.get_user(token)
        if user and hasattr(user, 'user'):
            return {
                'id': user.user.id,
                'email': user.user.email,
                'metadata': user.user.user_metadata,
            }
    except Exception as e:
        # JWT is invalid or expired
        return None
    
    return None


# ---------------------------------------------------------------------------
# Unified auth decorator
# ---------------------------------------------------------------------------

def require_auth(f):
    """
    Decorator to require authentication.
    
    In Supabase mode: checks Authorization header for JWT
    In password mode: checks session for 'authenticated' flag
    In no-auth mode (neither configured): allows access
    """
    from functools import wraps
    
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if Supabase mode
        if SUPABASE_URL and SUPABASE_SERVICE_KEY:
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Unauthorized'}), 401
            
            user = verify_supabase_jwt(token)
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Attach user info to request context
            request.user_id = user['id']
            request.user_email = user.get('email')
            request.auth_mode = 'supabase'
        
        # Check if password mode
        elif USE_PASSWORD_AUTH:
            if not session.get('authenticated'):
                return jsonify({'error': 'Unauthorized'}), 401
            request.user_id = '00000000-0000-0000-0000-000000000001'  # local user
            request.auth_mode = 'password'
        
        # No auth mode (neither configured)
        else:
            request.user_id = '00000000-0000-0000-0000-000000000001'
            request.auth_mode = 'none'
        
        return f(*args, **kwargs)
    
    return decorated


# ---------------------------------------------------------------------------
# Login/logout endpoints
# ---------------------------------------------------------------------------

def login_endpoint():
    """Handle login requests."""
    data = request.json
    entered_password = data.get('password', '') if data else ''
    
    # Supabase mode: use Supabase auth
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        email = data.get('email', '')
        password = data.get('password', '')
        
        try:
            client = get_supabase_client()
            response = client.auth.sign_in_with_password({
                'email': email,
                'password': password,
            })
            if response and hasattr(response, 'session') and response.session:
                # Return the access token for the frontend to use
                return jsonify({
                    'status': 'authenticated',
                    'token': response.session.access_token,
                    'user_id': response.session.user.id,
                })
        except Exception as e:
            return jsonify({'status': 'unauthorized', 'error': 'Invalid credentials'}), 401
    
    # Password mode: check .env password
    elif USE_PASSWORD_AUTH:
        if entered_password == PASSWORD_HASH:
            session['authenticated'] = True
            session.permanent = True
            return jsonify({'status': 'authenticated'})
        else:
            return jsonify({'status': 'unauthorized', 'error': 'Invalid password'}), 401
    
    # No auth mode: always allow
    else:
        session['authenticated'] = True
        return jsonify({'status': 'authenticated'})


def logout_endpoint():
    """Handle logout requests."""
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        # Supabase mode: clear token (frontend handles this)
        return jsonify({'status': 'logged_out'})
    else:
        # Password mode: clear session
        session.pop('authenticated', None)
        return jsonify({'status': 'logged_out'})


def status_endpoint():
    """Return auth status for the frontend."""
    auth_required = bool(SUPABASE_URL or USE_PASSWORD_AUTH)
    
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        # Supabase mode: check if token is valid
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if token:
            user = verify_supabase_jwt(token)
            authenticated = user is not None
        else:
            authenticated = False
    else:
        # Password mode: check session
        authenticated = session.get('authenticated', False)
    
    return jsonify({
        'authenticated': authenticated,
        'auth_required': auth_required,
        'auth_mode': 'supabase' if SUPABASE_URL and SUPABASE_SERVICE_KEY else ('password' if USE_PASSWORD_AUTH else 'none'),
    })
