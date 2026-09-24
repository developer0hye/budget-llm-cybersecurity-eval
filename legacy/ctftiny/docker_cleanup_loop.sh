#!/bin/bash
# Reclaims Docker disk during a long eval run. The full 1000-job run pulls a
# unique multi-GB image per challenge and crashed twice with ENOSPC before
# this existed (see README, Appendix B).
#
# Two rules learned on 2026-09-22, when this loop silently broke the
# 2019f-web-biometric gap-fill over and over:
#
# 1. Only prune when disk is actually tight. The original version deleted
#    every not-currently-running llmctf/* image every 180s, so a challenge
#    image pulled for the next job was often gone before the job started --
#    the job then died in docker compose with a 2-4s "No such image" failure
#    that looks exactly like an infrastructure flake in the results file.
# 2. Never delete images that cannot be re-pulled. llmctf/2019f-web-biometric-
#    biometric_client does not exist in the registry; it is built locally from
#    the challenge directory (with a patched Dockerfile). Deleting it means
#    the challenge stays broken until someone rebuilds it by hand.
MIN_FREE_GB_ROOT=8
MIN_FREE_GB_T7=25
KEEP_PATTERN='biometric_client'

free_gb() { df -g "$1" 2>/dev/null | awk 'NR==2 {print $4}'; }

while true; do
  sleep 180
  docker container prune -f > /dev/null 2>&1
  docker builder prune -f > /dev/null 2>&1

  root_free=$(free_gb /)
  t7_free=$(free_gb /Volumes/T7)
  [ -z "$t7_free" ] && t7_free=$MIN_FREE_GB_T7   # T7 unplugged: ignore that floor

  if [ "${root_free:-99}" -ge "$MIN_FREE_GB_ROOT" ] && [ "${t7_free:-99}" -ge "$MIN_FREE_GB_T7" ]; then
    continue   # plenty of room -- keep images cached for the next job
  fi

  in_use=$(docker ps --format "{{.Image}}")
  docker images --format "{{.Repository}}:{{.Tag}}" | grep "^llmctf/" | while read -r img; do
    echo "$img" | grep -q "$KEEP_PATTERN" && continue
    echo "$in_use" | grep -qF "$img" || echo "$img"
  done | xargs -r docker rmi > /dev/null 2>&1
done
