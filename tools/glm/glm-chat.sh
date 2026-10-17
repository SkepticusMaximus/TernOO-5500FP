#!/bin/bash
# Ask GLM a question.  Usage:  ./glm-chat.sh "what is balanced ternary?"
Q="${*:-Hello}"
PAYLOAD=$(python3 -c 'import json,sys; print(json.dumps({"model":"glm","messages":[{"role":"user","content":sys.argv[1]}],"max_tokens":512}))' "$Q")
echo "(GLM is a slow oracle — answers take minutes. Thinking...)"
curl -s --max-time 3600 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' -d "$PAYLOAD" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["choices"][0]["message"]["content"])' \
  2>/dev/null || echo "No response — is GLM up? Run ./glm-up.sh first."
