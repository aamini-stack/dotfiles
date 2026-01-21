#!/bin/bash
# Helper script for zjstatus git status
git update-index --assume-unchanged .config/zellij/layouts/minimal.kdl .config/zellij/layouts/dev.kdl 2>/dev/null
if git diff --quiet 2>/dev/null || git diff --cached --quiet 2>/dev/null; then
    echo "#[fg=#fab387]●"
else
    echo "#[fg=#a6e3a1]✓"
fi
