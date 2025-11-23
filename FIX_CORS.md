# Fixing CORS "Failed to Fetch" Error

## The Problem
The React app shows "API is offline" even though the backend is running. This is a CORS (Cross-Origin Resource Sharing) issue.

## The Solution

The backend needs to be restarted after CORS changes. The uvicorn server with `--reload` should pick up changes automatically, but if not:

1. **Stop the current backend** (Ctrl+C in the terminal running uvicorn)

2. **Restart the backend:**
```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
source venv312/bin/activate
python -m uvicorn web_api:app --reload --port 8000 --host 0.0.0.0
```

3. **Refresh your browser** - The React app should now detect the API as online.

## What Was Fixed

- ✅ CORS middleware configured with specific origins (localhost:3000, localhost:5173)
- ✅ Health endpoint returns proper JSON
- ✅ OPTIONS handler for preflight requests
- ✅ Better error handling in React app

## Verify It's Working

Check the browser console (F12) - you should see:
- No CORS errors
- Health check succeeding
- Green dot in header showing "online"

If you still see errors, check:
1. Backend is running on port 8000
2. Frontend is running on port 3000
3. Browser console for specific error messages

