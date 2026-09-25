#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Define colors
BLUE='\033[1;34m'
GREEN='\033[1;32m'
NC='\033[0m' # No Color
INFO="${BLUE}ℹ${NC}"
OK="${GREEN}✓${NC}"

# Remove any obsolete configuration if it remains from an older checkout.
rm -f uv.toml

# Detect if running on internal Linux (Rodete)
if [ -f "/etc/os-release" ] && grep -q "rodete" /etc/os-release; then
    echo -e "${INFO} Detected internal environment (Rodete)."

    # 1. Configure uv (Python)
    echo -e "${INFO} Configuring uv.toml..."
    cat <<EOF > uv.toml
[[index]]
name = "pypi"
url = "https://pypi.org/simple"
default = true
EOF

    # 2. Configure npm/bun (JavaScript)
    # We create/update .npmrc in the project root to set the registry.
    if [ ! -f ".npmrc" ]; then
         echo -e "${INFO} Creating .npmrc to force public NPM registry..."
         echo "registry=https://registry.npmjs.org" > .npmrc
         echo -e "${OK} .npmrc created."
    else
         if ! grep -q "registry=https://registry.npmjs.org" .npmrc; then
             echo "registry=https://registry.npmjs.org" >> .npmrc
             echo -e "${OK} Appended registry to .npmrc."
         else
             echo -e "${INFO} .npmrc already configured. Skipping."
         fi
    fi
else
    echo -e "${INFO} Not running on Rodete. Skipping specific internal environment setup for NPM."
fi
