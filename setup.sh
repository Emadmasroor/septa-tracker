#!/usr/bin/env bash

set -e  # stop on error
VENV_DIR="septa_venv"

# Add new Python packages here as needed
DEPENDENCIES=(
    requests
)

echo "Creating virtual environment (if not exists)..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
for pkg in "${DEPENDENCIES[@]}"; do
    pip install "$pkg"
done

echo "Saving requirements.txt..."
pip freeze > requirements.txt

echo ""
echo "Done."
echo "To activate later run:"
echo "source $VENV_DIR/bin/activate"
