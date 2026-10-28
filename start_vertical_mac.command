#!/bin/bash
set -e
cd "$(dirname "$0")"
exec bash ./start_mac.command --vertical
