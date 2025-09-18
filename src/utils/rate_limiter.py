from functools import wraps
from flask import current_app, request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
import threading

# In-memory rate limiting (for production, use Redis)
_rate_limits = defaultdict(lambda: defaultdict(list))
_lock = threading.Lock()

def rate_limit(key_prefix, per_minute=60, per_hour=None):
    """
    Rate limiting decorator
    
    Args:
        key_prefix: Prefix for the rate limit key
        per_minute: Maximum requests per minute
        per_hour: Maximum requests per hour (optional)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip rate limiting entirely when running in the testing configuration
            if current_app and current_app.config.get('TESTING'):
                return f(*args, **kwargs)

            # Get client identifier (IP address)
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            current_time = datetime.utcnow()
            minute_key = f"{key_prefix}:{client_ip}:minute"
            hour_key = f"{key_prefix}:{client_ip}:hour"
            
            with _lock:
                # Clean old entries and check minute limit
                minute_requests = _rate_limits[minute_key]['requests']
                minute_requests[:] = [req_time for req_time in minute_requests 
                                    if current_time - req_time < timedelta(minutes=1)]
                
                if len(minute_requests) >= per_minute:
                    return jsonify({
                        "ok": False,
                        "error": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Limit: {per_minute} per minute",
                        "retry_after": 60
                    }), 429
                
                # Check hour limit if specified
                if per_hour:
                    hour_requests = _rate_limits[hour_key]['requests']
                    hour_requests[:] = [req_time for req_time in hour_requests 
                                      if current_time - req_time < timedelta(hours=1)]
                    
                    if len(hour_requests) >= per_hour:
                        return jsonify({
                            "ok": False,
                            "error": "RATE_LIMIT_EXCEEDED",
                            "message": f"Too many requests. Limit: {per_hour} per hour",
                            "retry_after": 3600
                        }), 429
                    
                    hour_requests.append(current_time)
                
                # Record this request
                minute_requests.append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def clear_rate_limits():
    """Clear all rate limits (useful for testing)"""
    with _lock:
        _rate_limits.clear()

def get_rate_limit_status(key_prefix, client_ip):
    """Get current rate limit status for debugging"""
    current_time = datetime.utcnow()
    minute_key = f"{key_prefix}:{client_ip}:minute"
    hour_key = f"{key_prefix}:{client_ip}:hour"
    
    with _lock:
        minute_requests = _rate_limits[minute_key]['requests']
        minute_requests[:] = [req_time for req_time in minute_requests 
                            if current_time - req_time < timedelta(minutes=1)]
        
        hour_requests = _rate_limits[hour_key]['requests']
        hour_requests[:] = [req_time for req_time in hour_requests 
                          if current_time - req_time < timedelta(hours=1)]
        
        return {
            "minute_requests": len(minute_requests),
            "hour_requests": len(hour_requests),
            "last_request": max(minute_requests) if minute_requests else None
        }

class RateLimiter:
    """Rate limiter class for testing compatibility"""
    
    def __init__(self):
        self.limits = defaultdict(list)
    
    def is_allowed(self, key, limit=10, window=60):
        """Check if request is allowed within rate limit"""
        current_time = datetime.utcnow()
        
        # Clean old entries
        cutoff_time = current_time - timedelta(seconds=window)
        self.limits[key] = [req_time for req_time in self.limits[key] if req_time > cutoff_time]
        
        # Check if within limit
        if len(self.limits[key]) >= limit:
            remaining = 0
            reset_time = min(self.limits[key]) + timedelta(seconds=window)
            return False, remaining, reset_time
        
        # Record this request
        self.limits[key].append(current_time)
        remaining = limit - len(self.limits[key])
        reset_time = current_time + timedelta(seconds=window)
        
        return True, remaining, reset_time
