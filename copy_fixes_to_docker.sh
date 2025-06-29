#!/bin/bash
# Script to copy fixed files to Docker container

echo "Copying fixed surrogate modeling files to Docker container..."

# Find the container name (adjust the pattern if needed)
CONTAINER=$(docker ps --format "{{.Names}}" | grep -i "e_plus\|eplus" | head -1)

if [ -z "$CONTAINER" ]; then
    echo "Error: No running E_Plus container found."
    echo "Please provide container name as argument: $0 <container_name>"
    echo ""
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}"
    exit 1
fi

echo "Using container: $CONTAINER"
echo ""

# List of files to copy
FILES=(
    "c_surrogate/surrogate_data_extractor.py"
    "c_surrogate/surrogate_pipeline_tracker.py"
    "c_surrogate/surrogate_data_consolidator.py"
    "c_surrogate/surrogate_data_preprocessor.py"
    "c_surrogate/unified_surrogate.py"
)

# Copy each file
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -n "Copying $file... "
        docker cp "$file" "${CONTAINER}:/usr/src/app/${file}"
        if [ $? -eq 0 ]; then
            echo "✓"
        else
            echo "✗ Failed"
        fi
    else
        echo "Warning: $file not found"
    fi
done

echo ""
echo "Done! The surrogate modeling should now work correctly."
echo ""
echo "You can now run the surrogate modeling again."