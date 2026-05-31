#!/bin/bash
# Clear cache for RAG system demo

echo "Clearing caches..."
echo ""

# Clear Redis cache
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        redis-cli FLUSHDB > /dev/null
        echo "✓ Cleared Redis cache"
    else
        echo "⚠ Redis not running - skipping Redis cache clear"
    fi
else
    echo "⚠ redis-cli not found - skipping Redis cache clear"
fi

# Remove Chroma vector database
if [ -d "./chroma_db" ]; then
    rm -rf ./chroma_db
    echo "✓ Cleared Chroma vector database"
fi

echo ""
echo "Cache cleared - ready for fresh demo!"
echo ""
echo "Redis cache info:"
echo "  - View size: redis-cli DBSIZE"
echo "  - Monitor: redis-cli MONITOR"
