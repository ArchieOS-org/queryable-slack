# Vercel Authentication Fix

## Problem

After successful Vercel deployment, the `/api/chat` endpoint returns **401 "Authentication Required"** errors. Browser console shows:

```
Python API response status: 401
Conductor API error: 401 - <!doctype html><html lang=en>...Authentication Required...
Error querying Conductor: Error: Conductor API error: Unauthorized
```

The HTML response contains Vercel's deployment protection authentication page, indicating Python API endpoints are protected.

## Root Cause

**Vercel Deployment Protection** is enabled for preview deployments, which blocks all API routes including `/api/*` Python serverless functions.

## Solution Options (Ranked)

### OPTION 1: Deployment Protection Exceptions (RECOMMENDED - QUICKEST)

**Time**: 2 minutes
**Complexity**: Easiest - no code changes needed

**Steps**:

1. Go to **Vercel Dashboard** → Your Project → **Settings**
2. Navigate to **"Deployment Protection"** section in the left sidebar
3. Scroll to **"Deployment Protection Exceptions"**
4. Click **"Add Exception"**
5. Enter your preview deployment domain (e.g., `doha-nsd97-doha.vercel.app` or `*.vercel.app` for all previews)
6. Click **Save**

**Result**: Your preview deployment becomes publicly accessible without authentication. API calls will work immediately.

**Pros**:
- No code changes
- Works instantly
- No headers or secrets needed
- Perfect for public demos

**Cons**:
- Preview deployment is publicly accessible (fine for demos)
- Not suitable if preview contains sensitive data

---

### OPTION 2: Protection Bypass for Automation (RECOMMENDED - PRODUCTION)

**Time**: 15 minutes
**Complexity**: Moderate - requires frontend code changes

**Steps**:

1. **Generate bypass secret** in Vercel Dashboard:
   - Project Settings → Deployment Protection
   - Click **"Protection Bypass for Automation"**
   - Click **"Generate New Secret"**
   - Copy the secret (auto-saved as `VERCEL_AUTOMATION_BYPASS_SECRET`)

2. **Add secret to environment variables** (if not using system env):
   - Settings → Environment Variables
   - Add: `NEXT_PUBLIC_VERCEL_AUTOMATION_BYPASS_SECRET` = `<your-secret>`
   - Select **Preview** scope
   - Save and redeploy

3. **Update frontend API calls** to include bypass header:

   **Option A: Update client-side fetch calls**
   ```typescript
   // src/app/page.tsx or wherever you make API calls
   const bypassSecret = process.env.NEXT_PUBLIC_VERCEL_AUTOMATION_BYPASS_SECRET;

   const response = await fetch('/api/chat', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'x-vercel-protection-bypass': bypassSecret || '',
       'x-vercel-set-bypass-cookie': 'true'
     },
     body: JSON.stringify(data)
   });
   ```

   **Option B: Update API route middleware** (better for security)
   ```typescript
   // src/app/api/chat/route.ts
   export async function POST(req: Request) {
     const bypassSecret = process.env.VERCEL_AUTOMATION_BYPASS_SECRET;

     const response = await fetch('http://localhost:3000/api/index', {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json',
         'x-vercel-protection-bypass': bypassSecret || ''
       },
       body: await req.text()
     });

     return response;
   }
   ```

**Pros**:
- Secure - only authorized clients can bypass
- Production-ready
- Automatic via system env var `VERCEL_AUTOMATION_BYPASS_SECRET`

**Cons**:
- Requires code changes
- Secret can be exposed in client-side code (use Option B to avoid)

---

### OPTION 3: Disable Deployment Protection Entirely

**Time**: 1 minute
**Complexity**: Easiest - but less secure

**Steps**:

1. Go to **Vercel Dashboard** → Your Project → **Settings**
2. Navigate to **"Deployment Protection"**
3. Toggle **"Standard Protection"** to **OFF**
4. Save

**Result**: All preview deployments become publicly accessible.

**Pros**:
- Instant fix
- No code changes

**Cons**:
- All previews are public
- No protection for sensitive branches
- Not recommended for production projects

---

## Recommended Action Plan

### For Quick Testing (NOW):

**Use Option 1 - Deployment Protection Exceptions**

1. Add your preview domain to exceptions
2. Test `/api/chat` immediately - should work
3. Verify API calls succeed without 401 errors

### For Production Deployment:

**Use Option 2 - Protection Bypass for Automation**

1. Generate bypass secret
2. Update Next.js API routes to include header (server-side)
3. This keeps protection enabled while allowing your app to work

---

## Verification Steps

After implementing the fix:

1. **Open browser console** (DevTools → Console tab)
2. **Test API call**:
   ```javascript
   fetch('/api/chat', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       messages: [{ role: 'user', content: 'test' }]
     })
   })
   .then(r => r.json())
   .then(console.log)
   .catch(console.error)
   ```
3. **Expected**: Should return JSON response (not 401 HTML)
4. **Verify**: No "Authentication Required" errors in console

---

## Current Deployment Info

- **Preview URL**: https://doha-nsd97-doha.vercel.app (or similar)
- **Branch**: nsd97/doha
- **Framework**: Next.js 15.3.1
- **API**: Python serverless at `/api/*`

---

## Next Steps After Fix

1. ✅ Add preview domain to Deployment Protection Exceptions
2. ✅ Test `/api/chat` endpoint
3. ✅ Verify Python backend responds correctly
4. ✅ Test UI functionality
5. ✅ Create PR to main branch
6. ✅ Deploy to production

---

**Current Status**: Waiting for user to apply Option 1 fix in Vercel dashboard.
