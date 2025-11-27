# Deployment Fix - Path Duplication Error

## Problem Identified

The Vercel deployment failed with:
```
Error: ENOENT: no such file or directory, lstat '/vercel/path0/path0/.next/routes-manifest.json'
```

**Root Cause**: The path shows duplication (`path0/path0/`), indicating Vercel has incorrect project settings.

## Current Vercel Settings (INCORRECT):
- **Framework Preset**: "Other" ❌
- **Root Directory**: Empty ✓ (actually correct)
- **Build Command**: Uses overrides ❌

## Required Fixes

### Option 1: Fix via Vercel Dashboard (Recommended)

1. **Go to Project Settings**:
   - URL: https://vercel.com/nsd97s-projects/doha/settings

2. **Update Build & Development Settings**:
   - Click "General" → "Build & Development Settings"
   - **Framework Preset**: Change from "Other" to **"Next.js"**
   - **Build Command**: Remove override (click "X" if present)
   - **Output Directory**: Remove override (should auto-detect `.next`)
   - **Install Command**: Keep as `pnpm install` or let auto-detect
   - Click **Save**

3. **Verify Root Directory**:
   - In "General" → "Root Directory"
   - Ensure it's **empty** or set to `.`
   - Click **Save**

4. **Redeploy**:
   ```bash
   cd /Users/noahdeskin/conductor/queryable-slack-2/.conductor/doha
   vercel --yes
   ```

### Option 2: Delete and Recreate Project

If the above doesn't work:

1. **Delete the "doha" project** in Vercel dashboard
2. **Recreate by redeploying**:
   ```bash
   cd /Users/noahdeskin/conductor/queryable-slack-2/.conductor/doha
   rm -rf .vercel
   vercel --yes
   ```
3. When prompted:
   - Link to existing project? **No**
   - Project name: `doha`
   - Framework: Let it auto-detect **Next.js**

### Option 3: Use Parent Directory Instead

Deploy from the parent directory (which is NOT a worktree):

```bash
cd /Users/noahdeskin/conductor/queryable-slack-2
rm -rf .vercel
vercel --yes
```

This will create a fresh Vercel project with correct settings.

## Why This Happened

The Vercel project was originally configured when the structure had:
- `frontend/` directory as root
- Different build paths

After reorganization, Vercel still has cached settings pointing to the old structure.

## Verification After Fix

Once redeployed successfully, verify:

1. **Build succeeds**: No path duplication errors
2. **Frontend loads**: https://doha-xxx.vercel.app shows the chat interface
3. **API works**: Can call `/api/debug` endpoint
4. **Python functions work**: Import from `conductor/` package succeeds

## Current Project Structure (Correct)

```
.conductor/doha/  (or parent directory)
├── src/          # Next.js frontend
│   ├── app/
│   ├── components/
│   └── lib/
├── api/          # Python serverless
├── conductor/    # Python package
├── public/
├── vercel.json   # Correct config
└── package.json
```

## Next Steps After Fix

1. ✅ Deploy successfully to preview
2. ✅ Test all endpoints
3. ✅ Create PR from nsd97/doha → main
4. ✅ Deploy to production

---

**Recommendation**: Try Option 1 first (dashboard settings). If that doesn't work, use Option 3 (deploy from parent directory).
