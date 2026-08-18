#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf dist-site
mkdir -p dist-site
cp index.html dist-site/
cp favicon.ico dist-site/
cp google4d56ef11b86317e2.html dist-site/

echo "Built dist-site/ ($(ls dist-site | wc -l | tr -d ' ') files)"
