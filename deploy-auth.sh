#!/bin/bash

# Deploy Script for evidens.digital Authentication System
# This script prepares and deploys the authentication system to Vercel

echo "🚀 Starting deployment of evidens.digital Authentication System..."

# Check if we're in the correct directory
if [ ! -f "app_with_auth.py" ]; then
    echo "❌ Error: app_with_auth.py not found. Please run this script from the project root."
    exit 1
fi

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

# Create production database if it doesn't exist
echo "🗄️ Setting up production database..."
if [ ! -f "src/database/app.db" ]; then
    python3 init_auth_database.py
fi

# Copy the auth-specific vercel.json
echo "⚙️ Configuring Vercel settings..."
cp vercel-auth.json vercel.json

# Set environment variables (these should be set in Vercel dashboard)
echo "🔐 Environment variables that need to be set in Vercel dashboard:"
echo "  - SECRET_KEY: A secure random string"
echo "  - GOOGLE_CLIENT_ID: Google OAuth client ID"
echo "  - GOOGLE_CLIENT_SECRET: Google OAuth client secret"
echo "  - APPLE_CLIENT_ID: Apple OAuth client ID (optional)"
echo "  - APPLE_CLIENT_SECRET: Apple OAuth client secret (optional)"

# Deploy to Vercel
echo "🌐 Deploying to Vercel..."
vercel --prod

echo "✅ Deployment completed!"
echo ""
echo "📋 Post-deployment checklist:"
echo "  1. Set environment variables in Vercel dashboard"
echo "  2. Test login functionality"
echo "  3. Verify OAuth providers work"
echo "  4. Check database connectivity"
echo "  5. Test logout functionality"
echo ""
echo "🔗 Don't forget to update DNS settings if using custom domain!"
