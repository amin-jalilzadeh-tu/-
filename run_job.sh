#!/bin/bash

# This script assumes you have combined.json in the current directory.
# And that your app is running on localhost:8000 in Docker.

# 1) Read combined.json as a single string
postData=$(cat combined.json)

# 2) Create the job
echo "Creating job..."
createResponse=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "@combined.json" \
    http://localhost:8000/jobs)

# 3) Extract the job_id
jobId=$(echo "$createResponse" | jq -r '.job_id')
echo "Created job with ID: $jobId"

# 4) Start the job
echo "Starting job..."
startResponse=$(curl -s -X POST \
    http://localhost:8000/jobs/$jobId/start)
echo "$startResponse" | jq .

# 5) Stream logs in real time
echo "Streaming logs..."
curl http://localhost:8000/jobs/$jobId/logs