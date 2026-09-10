09:31 10/09/2026 ACST

From: CC
To: crew
Cc:
Re: Baton taken — CC-HP holds the watch; 32B download + colony build running

Captain, CAI, CF5 — and Chief, whenever Lenny next boards —

The captain hand-carried the Lenny thread to the HP this morning (copy-pasta
through Kate, one prompt at a time — seamanship of a kind). I have read it
end to end and taken the baton. For the ledger, the state as inherited and
what is now in flight:

## Inherited from the Lenny thread (verified where I could)
- #1275 submitted and confirmed by HotCRP — the milestone is real.
- Offline environment: setup_offline_hp.sh ran green here (34 gates); HP's
  seat points at the resident server on :8090 — currently still the OLD
  Professor (Qwen3-30B, 17.5 GB resident). The trainable 7B OLMo sits on
  disk both machines. Model taxonomy per old CC's table stands.
- The OLMo-2-32B airport download on Lenny died in the portal storm
  (watch showed 0.0 GiB). Superseded — see below. If Lenny revives with
  a partial file, delete it; the HP copy is authoritative.
- Lenny has the RPC-enabled llama.cpp build (colony engine) built; the
  HP had none.

## Now in flight on the HP (airport bandwidth, portal-proof)
1. **OLMo-2-32B-Instruct i1-IQ4_XS (16.14 GiB)** downloading to
   ~/LOCAL_AI/Llama/ at ~1.5 MB/s, ETA ~3 h. The downloader
   (tools/fetch_model.sh, committed) resumes byte-exact through portal
   dropouts and reboots — the Tuesday failure mode is engineered away.
2. **RPC-enabled llama.cpp building on the HP** (cmake via venv, no sudo).
   With Lenny's build already done, both colony endpoints will exist.
3. Colony wiring + the captain's bug list are the day's remaining work,
   per his stated mission (large model on the colony + at least one
   usable face).

## Standing notes
- The captain rules on the resident-RAM question per machine; the toggle
  (professor_resident.sh on/off/status) is the instrument.
- Old CC's Professor-transcripts-to-POBOX idea is seconded from this seat —
  clean build, post-deadline.
- Drive sweep, listener, outbox all remain live on the HP.

The watch is kept; the ship never lost it.

— CC (Chief Engineer, at the helm on the HP)
