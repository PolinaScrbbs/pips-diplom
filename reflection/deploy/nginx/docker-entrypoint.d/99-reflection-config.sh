#!/bin/sh
set -e

DOMAIN="${LE_DOMAIN:-localhost}"
MODE="${NGINX_MODE:-http-only}"
TEMPLATE_DIR="/etc/nginx/reflection-templates"
OUT="/etc/nginx/conf.d/default.conf"

if [ "$MODE" = "https" ]; then
  sed "s/__LE_DOMAIN__/${DOMAIN}/g" "${TEMPLATE_DIR}/http-and-https.conf.template" >"${OUT}"
else
  sed "s/__LE_DOMAIN__/${DOMAIN}/g" "${TEMPLATE_DIR}/http-only.conf.template" >"${OUT}"
fi
