#!/bin/bash
# GLM-5.2 cluster launcher — run on Huey when you want to use GLM.
#   ./glm-up.sh
# Needs the Pi plugged into Huey (USB-C) and ethernet Pi->Lenny.
PI=10.55.0.1; LENNY=10.55.1.2; WP=9100
echo "[1/3] network..."
ping -c1 -W2 $PI >/dev/null 2>&1 || { echo "  Pi not up at $PI — plug its USB-C into Huey, wait ~90s, retry."; exit 1; }
ip route | grep -q '10.55.1.0' || { echo "  adding route to Lenny (enter your password):"; sudo ip route add 10.55.1.0/24 via $PI; }
ping -c1 -W2 $LENNY >/dev/null 2>&1 || { echo "  Lenny not reachable over the wire — check the ethernet cable Pi<->Lenny."; exit 1; }
echo "[2/3] worker on Lenny..."
ssh -o ConnectTimeout=8 steven@$LENNY 'pgrep -f "cluster worker" >/dev/null' 2>/dev/null \
  || ssh steven@$LENNY "setsid --fork bash -c 'cd ~/colibri && exec python3 c/coli cluster worker --model /mnt/glm --port $WP --advertise-host $LENNY >~/colibri-worker.log 2>&1 </dev/null'"
sleep 3
echo "[3/3] coordinator (loads ~12GB dense core, ~1-2 min)..."
pkill -f "coli serve" 2>/dev/null; sleep 1
setsid --fork bash -c "cd ~/colibri && export COLI_RAM_OVERCOMMIT=1 && exec python3 c/coli serve --model ~/glm-local --gpu none --ctx 8192 --cluster-workers $LENNY:$WP --host 0.0.0.0 --port 8000 >~/colibri-coord.log 2>&1 </dev/null"
for i in $(seq 1 60); do
  ss -ltn 2>/dev/null | grep -q :8000 && { echo "GLM READY  ->  ask it with:  ~/glm-chat.sh \"your question\""; exit 0; }
  grep -q "refusing to start" ~/colibri-coord.log 2>/dev/null && { echo "NOT ENOUGH FREE RAM. Close your browser/apps (need ~20GB free), then re-run ./glm-up.sh"; exit 1; }
  grep -qi "exited unexpectedly" ~/colibri-coord.log 2>/dev/null && ! grep -q refusing ~/colibri-coord.log && { echo "engine error — see ~/colibri-coord.log"; exit 1; }
  sleep 3
done
echo "timed out; see ~/colibri-coord.log"
