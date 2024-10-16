#!/bin/sh
echo "Running vite build..."
if vite build; then
  echo "Vite build successful."
else
  echo "Vite build failed. Exiting."
  exit 1
fi

