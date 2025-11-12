#!/bin/bash
# Notification handler script for DocOrchestrator review
# Called when user clicks "Review" notification
# Usage: review_notification_handler.sh <session_id>

SESSION_ID=$1

if [ -z "$SESSION_ID" ]; then
    echo "Error: No session ID provided"
    exit 1
fi

# Path to DocOrchestrator
ORCHESTRATOR_DIR="$HOME/Development/Scripts/DocOrchestrator"

# Build the review command
REVIEW_CMD="cd $ORCHESTRATOR_DIR && python3 orchestrator.py --review --session $SESSION_ID"

# Open Terminal and run the command
osascript <<EOF
tell application "Terminal"
    activate
    do script "$REVIEW_CMD"
end tell
EOF
