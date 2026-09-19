#!/bin/bash
while true; do
  sleep 180
  docker container prune -f > /dev/null 2>&1
  docker builder prune -f > /dev/null 2>&1
  in_use=$(docker ps --format "{{.Image}}")
  docker images --format "{{.Repository}}:{{.Tag}}" | grep "^llmctf/" | while read img; do
    echo "$in_use" | grep -qF "$img" || echo "$img"
  done | xargs -r docker rmi > /dev/null 2>&1
done
