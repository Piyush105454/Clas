#!/bin/bash
# Easy static files collection script

echo "🧹 Clearing old static files..."
rm -rf staticfiles/

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Done! Static files collected and ready."
