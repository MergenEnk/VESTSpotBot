#!/bin/bash

# Test script for Railway deployment
URL="https://vestspotbot-production.up.railway.app"

echo "Testing Railway deployment..."
echo ""

echo "1. Testing root endpoint..."
curl -s "$URL/" | python3 -m json.tool
echo ""

echo "2. Testing health endpoint..."
curl -s "$URL/health" | python3 -m json.tool
echo ""

echo "3. Testing Slack events endpoint (should return error without proper Slack signature)..."
curl -s -X POST "$URL/slack/events" \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123"}' 
echo ""

