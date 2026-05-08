#!/bin/bash
# PreToolUse hook for Bash: append every command Claude runs to
# ai.bashcommands.log at the project root. The log is gitignored so it
# never reaches origin; it exists so the user can backtrack what
# Claude did across a session.
#
# Hook input arrives as JSON on stdin; tool_input.command holds the
# actual shell string. We capture via jq.

set -u

LOG_FILE="${CLAUDE_PROJECT_DIR:-.}/ai.bashcommands.log"

COMMAND=$(jq -r '.tool_input.command // empty' 2>/dev/null)
TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

if [ -n "$COMMAND" ]; then
    {
        echo "$TIMESTAMP"
        # Indent the command block so multi-line commands stay readable.
        echo "$COMMAND" | sed 's/^/  /'
        echo "---"
    } >> "$LOG_FILE"
fi

# Always exit 0 so the hook never blocks a tool call (the deny list,
# not this logger, is what's responsible for blocking).
exit 0
