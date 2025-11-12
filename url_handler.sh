#!/bin/bash
# Qwilo URL Handler
# Handles custom URL scheme: qwilo://action?params

URL="$1"

# Parse the URL
# Format: qwilo://review-ideas?session=20251112_123600
# or: qwilo://view-documents?session=20251112_123600

# Remove the scheme
URL_NO_SCHEME="${URL#qwilo://}"

# Extract action and parameters
ACTION="${URL_NO_SCHEME%%\?*}"
PARAMS="${URL_NO_SCHEME#*\?}"

# DocOrchestrator directory
ORCHESTRATOR_DIR="$HOME/Development/Scripts/DocOrchestrationScheduler"

case "$ACTION" in
    review-ideas)
        # Extract session ID
        SESSION_ID="${PARAMS#*session=}"
        SESSION_ID="${SESSION_ID%%&*}"

        # Build command to review ideas
        CMD="cd '$ORCHESTRATOR_DIR' && python3 ../DocOrchestrator/orchestrator.py --review --session $SESSION_ID"

        # Open Terminal and run command
        osascript <<EOF
tell application "Terminal"
    activate
    do script "$CMD"
end tell
EOF
        ;;

    view-documents)
        # Extract session ID
        SESSION_ID="${PARAMS#*session=}"
        SESSION_ID="${SESSION_ID%%&*}"

        # Open the output directory for this session
        OUTPUT_PATH="$ORCHESTRATOR_DIR/output"

        # Open in Finder
        open "$OUTPUT_PATH"
        ;;

    *)
        osascript -e 'display notification "Unknown action: '"$ACTION"'" with title "Qwilo"'
        ;;
esac
