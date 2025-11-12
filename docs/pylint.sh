#!/bin/bash

echo "======================================="
echo "         Running Pylint                "
echo "======================================="

echo "\nLinting app/api..."
pylint --rc-file .pylintrc app/api/*

echo "\nLinting app/client..."
pylint --rc-file .pylintrc app/client/*

echo "\nLinting app/config..."
pylint --rc-file .pylintrc app/config/*

echo "\nLinting app/exception..."
pylint --rc-file .pylintrc app/exception/*

echo "\nLinting app/helper..."
pylint --rc-file .pylintrc app/helper/*

echo "\nLinting app/middleware..."
pylint --rc-file .pylintrc app/middleware/*

echo "\nLinting app/model..."
pylint --rc-file .pylintrc app/model/*

echo "\nLinting app/repository..."
pylint --rc-file .pylintrc app/repository/*

echo "\nLinting app/schema..."
pylint --rc-file .pylintrc app/schema/*

echo "\nLinting app/service..."
pylint --rc-file .pylintrc app/service/*

echo "\nLinting app/main.py..."
pylint --rc-file .pylintrc app/main.py

echo "\nLinting run.py..."
pylint --rc-file .pylintrc run.py

echo "======================================="
echo "         Pylint Complete               "
echo "======================================="
