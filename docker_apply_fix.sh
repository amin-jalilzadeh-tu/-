#!/bin/bash
# Script to apply surrogate modeling fixes to Docker container

echo "Applying surrogate modeling fixes to Docker container..."

# Get container name
CONTAINER_NAME=$(docker ps --format "table {{.Names}}" | grep -E "e_plus|eplus" | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "Error: Could not find running E_Plus container"
    echo "Please specify container name as argument: $0 <container_name>"
    exit 1
fi

echo "Found container: $CONTAINER_NAME"

# Copy fixed files to container
echo "Copying fixed files..."

# Copy the main fix
docker cp c_surrogate/surrogate_data_extractor.py ${CONTAINER_NAME}:/usr/src/app/c_surrogate/surrogate_data_extractor.py
if [ $? -eq 0 ]; then
    echo "✓ Copied surrogate_data_extractor.py"
else
    echo "✗ Failed to copy surrogate_data_extractor.py"
fi

# Copy the consolidator (new file)
docker cp c_surrogate/surrogate_data_consolidator.py ${CONTAINER_NAME}:/usr/src/app/c_surrogate/surrogate_data_consolidator.py
if [ $? -eq 0 ]; then
    echo "✓ Copied surrogate_data_consolidator.py"
else
    echo "✗ Failed to copy surrogate_data_consolidator.py"
fi

# Copy the updated preprocessor
docker cp c_surrogate/surrogate_data_preprocessor.py ${CONTAINER_NAME}:/usr/src/app/c_surrogate/surrogate_data_preprocessor.py
if [ $? -eq 0 ]; then
    echo "✓ Copied surrogate_data_preprocessor.py"
else
    echo "✗ Failed to copy surrogate_data_preprocessor.py"
fi

# Copy the updated unified surrogate
docker cp c_surrogate/unified_surrogate.py ${CONTAINER_NAME}:/usr/src/app/c_surrogate/unified_surrogate.py
if [ $? -eq 0 ]; then
    echo "✓ Copied unified_surrogate.py"
else
    echo "✗ Failed to copy unified_surrogate.py"
fi

echo ""
echo "Fixes applied! The surrogate modeling should now work correctly."
echo ""
echo "To test, you can run the surrogate modeling again."
echo ""
echo "If you need to rebuild the image to make changes permanent:"
echo "  docker-compose build"
echo "  docker-compose up -d"