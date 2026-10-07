#!/bin/sh
set -e

# Ensure persistent data directory exists
mkdir -p /app/data

# If the database does not exist in the mounted volume, seed it from the existing template
if [ ! -f /app/data/interview.db ] && [ -f /app/backend/interview.db ]; then
    echo "Seeding persistent database from template..."
    cp /app/backend/interview.db /app/data/interview.db
fi

exec "$@"
