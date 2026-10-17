# GLM appliance environment — sourced from stevo's ~/.profile on Huey.
#
# glm.service starts the coordinator with `runuser -l stevo`, i.e. a LOGIN
# shell, so this file is where the coordinator picks up its configuration
# without needing root to edit the unit.
#
# `coli serve` refuses to bind 0.0.0.0 with no auth, and Huey sits on the house
# wifi as well as the cluster link — so the API gets a key rather than an open
# port. The key lives in ~/.glm-api-key (mode 600); clients send it as
# `Authorization: Bearer <key>`.
if [ -r "$HOME/.glm-api-key" ]; then
  COLI_API_KEY=$(cat "$HOME/.glm-api-key")
  export COLI_API_KEY
fi
