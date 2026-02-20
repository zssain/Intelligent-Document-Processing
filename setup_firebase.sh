#!/bin/bash
# Quick setup script for Firebase integration
# Run this after configuring your .env files

set -e  # Exit on error

echo "🚀 Firebase Integration Setup"
echo "=============================="
echo ""

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI not found. Installing..."
    npm install -g firebase-tools
else
    echo "✅ Firebase CLI installed"
fi

# Frontend setup
echo ""
echo "📦 Installing frontend dependencies..."
cd bluetide-ui
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env from .env.example - please fill in your Firebase config!"
    cp .env.example .env
fi
npm install
cd ..

# Backend setup
echo ""
echo "📦 Installing backend dependencies..."
cd backend
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env from .env.example - please fill in your Firebase config!"
    cp .env.example .env
fi
pip install -e .
cd ..

# Cloud Functions setup
echo ""
echo "📦 Installing Cloud Functions dependencies..."
cd functions
npm install
cd ..

echo ""
echo "✅ Dependencies installed!"
echo ""
echo "📋 Next steps:"
echo "   1. Update .firebaserc with your project ID"
echo "   2. Fill in environment variables in:"
echo "      - bluetide-ui/.env"
echo "      - backend/.env"
echo "   3. Login to Firebase: firebase login"
echo "   4. Deploy functions: firebase deploy --only functions"
echo "   5. Create first user via UI signup"
echo "   6. Promote to admin: cd backend && python scripts/seed_admin.py --email admin@example.com"
echo ""
echo "📖 See FIREBASE_SETUP.md for detailed instructions"
