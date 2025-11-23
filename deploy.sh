#!/bin/bash
# Deployment script for Vercel + Supabase

set -e

echo "🚀 Starting deployment process..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install supabase/tap/supabase
    else
        echo "Please install Supabase CLI manually: https://github.com/supabase/cli#install-the-cli"
        exit 1
    fi
fi

echo "✅ CLIs installed"

# Step 1: Build frontend
echo "📦 Building frontend..."
cd web
npm install
npm run build
cd ..

# Step 2: Check environment variables
echo "🔍 Checking environment variables..."
required_vars=("ANTHROPIC_API_KEY" "SUPABASE_URL" "SUPABASE_ANON_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "⚠️  Missing environment variables: ${missing_vars[*]}"
    echo "Please set them with: vercel env add <VAR_NAME>"
    exit 1
fi

# Step 3: Deploy to Vercel
echo "🚀 Deploying to Vercel..."
if [ "$1" == "--prod" ]; then
    vercel --prod
else
    vercel
fi

echo "✅ Deployment complete!"
echo "📝 Next steps:"
echo "   1. Set environment variables in Vercel dashboard"
echo "   2. Upload ChromaDB data to Supabase storage"
echo "   3. Test the API endpoint"

