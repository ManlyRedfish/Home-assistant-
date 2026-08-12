#!/bin/sh
set -eu

# Official Home Assistant Core 2026.8.1 image. The digest prevents the proof
# substrate from changing while retaining the human-readable release tag.
image="ghcr.io/home-assistant/home-assistant:2026.8.1@sha256:6340a3de3917a9b19368e767310a96dd090f6a19aca8aeadf87fd1145cec9682"
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

docker run --rm \
  --entrypoint python3 \
  --mount "type=bind,src=$repo_root/tests/native_core_failure_injection.py,dst=/proof/native_core_failure_injection.py,readonly" \
  "$image" \
  /proof/native_core_failure_injection.py
