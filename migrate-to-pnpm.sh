#!/bin/bash
# Migration script to switch from npm to pnpm for enhanced security

echo "🔒 Migrating WireGate to pnpm for enhanced security..."

# Install pnpm globally
npm install -g pnpm

# Navigate to frontend directory
cd Src/static/app

# Remove npm lockfile
rm -f package-lock.json

# Remove node_modules
rm -rf node_modules

# Install dependencies with pnpm
echo "Installing dependencies with pnpm..."
pnpm install

# Generate pnpm lockfile
pnpm install --frozen-lockfile

echo "✅ Migration to pnpm complete!"
echo "📦 Using pnpm for all future package management"
echo "🔒 Enhanced security with content-addressable storage"
