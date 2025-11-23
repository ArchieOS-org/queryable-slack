# Local Network Access Setup

## Overview
The web app is now configured to be accessible from devices on your local network (like your iPhone).

## Configuration Changes

### FastAPI Backend
- **Host**: Bound to `0.0.0.0` (all network interfaces)
- **CORS**: Allows all origins for development (supports local network IPs)
- **Port**: 8000

### Vite Frontend
- **Host**: Bound to `0.0.0.0` (all network interfaces)
- **Port**: 3000
- **Auto-detects**: API URL based on hostname (uses IP when accessed via IP)

## How to Use

### 1. Start the Web App
```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
./start_web.sh
```

The script will display:
- Local URLs (for desktop): `http://localhost:3000`
- Network URLs (for mobile): `http://192.168.68.76:3000`

### 2. Access from iPhone

1. **Make sure iPhone is on the same Wi-Fi network** as your Mac
2. **Open Safari** on your iPhone
3. **Navigate to**: `http://192.168.68.76:3000`
   - Replace `192.168.68.76` with your Mac's IP address (shown in terminal)

### 3. Find Your Mac's IP Address

If you need to find your Mac's IP address:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

Or check the terminal output when running `start_web.sh` - it displays the network URL.

## Troubleshooting

### "Failed to fetch" on iPhone
- **Check**: Both devices are on the same Wi-Fi network
- **Check**: Mac firewall isn't blocking ports 3000 and 8000
- **Check**: Backend is running (`http://192.168.68.76:8000/health`)

### Can't connect from iPhone
- **Firewall**: System Preferences → Security & Privacy → Firewall
  - Allow incoming connections for Python/uvicorn
  - Or temporarily disable firewall for testing

### API shows offline on iPhone
- The React app auto-detects the API URL based on hostname
- If accessing via `http://192.168.68.76:3000`, it will use `http://192.168.68.76:8000` for API calls
- Verify backend is accessible: `http://192.168.68.76:8000/health`

## Security Note

⚠️ **Development Only**: The current CORS configuration allows all origins. For production:
- Restrict CORS to specific domains
- Use HTTPS
- Implement proper authentication

## Manual Start (if script doesn't work)

### Backend:
```bash
source venv312/bin/activate
python -m uvicorn web_api:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend:
```bash
cd web
npm run dev
```

Then access from iPhone: `http://YOUR_MAC_IP:3000`

