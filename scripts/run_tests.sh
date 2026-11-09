#!/bin/bash
# run_tests.sh - checks Ganache is running, then runs the Python test script
# and saves the output as evidence.
# Usage (Git Bash, from the repo folder):  bash scripts/run_tests.sh

URL="http://127.0.0.1:8545"
OUT="scripts/test_output.txt"

echo "Checking Ganache at $URL ..."
if ! curl -s -X POST -H "Content-Type: application/json" \
     --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' "$URL" > /dev/null; then
    echo "Ganache is not running. Open another terminal and run: ganache"
    exit 1
fi
echo "Ganache is running."
echo

# Prefer Python 3.12 on Windows (web3.py has no ready-made build for 3.15 yet),
# otherwise 'python', or 'python3' on Mac/Linux
if command -v py >/dev/null 2>&1 && py -3.12 --version >/dev/null 2>&1; then
    PY="py -3.12"
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    PY=python3
fi
echo "Using: $($PY --version)"

$PY scripts/interact.py | tee "$OUT"
echo
echo "Output saved to $OUT ($(date))" | tee -a "$OUT"
