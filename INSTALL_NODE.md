# Installing Node.js for Web App

## Quick Install (Recommended)

### Option 1: Using Homebrew (Easiest)

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Node.js
brew install node
```

### Option 2: Using nvm (Node Version Manager)

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Restart terminal or run:
source ~/.zshrc

# Install latest LTS Node.js
nvm install --lts
nvm use --lts
```

### Option 3: Direct Download

1. Visit https://nodejs.org/
2. Download the LTS version for macOS
3. Run the installer
4. Restart terminal

## Verify Installation

```bash
node --version
npm --version
```

You should see version numbers (e.g., `v20.x.x` and `10.x.x`)

## After Installing Node.js

```bash
cd /Volumes/LaCie/Coding-Projects/queryable-slack
cd web
npm install
cd ..
./start_web.sh
```

## Troubleshooting

If `npm` still not found after installing:
1. Restart your terminal
2. Check PATH: `echo $PATH`
3. Verify installation: `which node` and `which npm`

