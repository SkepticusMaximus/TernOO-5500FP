#!/usr/bin/env python3
"""Does the TernOO word layer cost us anything at GUI scale? Pure-python baseline."""
import time
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ternword as W

N = 200000
t = time.perf_counter()
for i in range(N):
    W.to_trits(i - N // 2)
enc = time.perf_counter() - t

ts = W.to_trits(W.SAMPLE)
t = time.perf_counter()
for _ in range(N):
    W.decode_primary(ts)
dec = time.perf_counter() - t

print("WORD encode (int -> 24 balanced-ternary trits): %.0f ns/word  (%.2f M words/s)"
      % (enc / N * 1e9, N / enc / 1e6))
print("WORD primary-decode (T23,T22 -> primary):        %.0f ns/word  (%.2f M words/s)"
      % (dec / N * 1e9, N / dec / 1e6))
print("context: a 60 fps frame budget is 16,700,000 ns; one full 24-trit encode is ~%.0f ns"
      % (enc / N * 1e9))
print("=> you could encode ~%.0f whole words inside a single frame and never drop it."
      % (16.7e-3 / (enc / N)))
