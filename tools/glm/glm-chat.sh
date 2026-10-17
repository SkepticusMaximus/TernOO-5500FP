#!/bin/bash
# Ask GLM a question.  Usage:  ./glm-chat.sh "what is balanced ternary?"
#
# Two things the first version got wrong, both of which made every ask fail:
#   - the model id is "glm-5.2-colibri", not "glm" (coli answered
#     {"error": "The model `glm` does not exist."} for every question);
#   - the API now requires a bearer key, because the server refuses to bind
#     beyond localhost unauthenticated and Huey is on the house wifi too.
Q="${*:-Hello}"
MODEL="${GLM_MODEL:-glm-5.2-colibri}"
BASE="${GLM_BASE:-http://127.0.0.1:8000}"
KEY="${COLI_API_KEY:-$(cat "$HOME/.glm-api-key" 2>/dev/null)}"

PAYLOAD=$(python3 -c 'import json,sys; print(json.dumps({"model":sys.argv[2],"messages":[{"role":"user","content":sys.argv[1]}],"max_tokens":256}))' "$Q" "$MODEL")
echo "(GLM is a slow oracle — a 744B MoE streaming experts off disk. Expect"
echo " many minutes per answer, not seconds. Thinking...)"
curl -sS --max-time 7200 "$BASE/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $KEY" \
  -d "$PAYLOAD" \
  | python3 -c 'import json,sys
d = json.load(sys.stdin)
if "error" in d:
    print("GLM refused the request:", d["error"].get("message", d["error"]))
    sys.exit(1)
print(d["choices"][0]["message"]["content"])' \
  || echo "No usable response — is GLM up? Check: systemctl status glm"
