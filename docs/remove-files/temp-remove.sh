#!/bin/bash

# This script removes specified files and directories.

# Remove individual files
rm -f .env
rm -f .env.dev
rm -f README.md
rm -f app/api/v1/router.py
rm -f app/config/constants.py

# Remove directory
rm -rf alembic/versions
