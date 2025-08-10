#!/bin/bash

# Increment patch version in pyproject.toml
current_version=$(grep -E '^version = "[0-9]+\.[0-9]+\.[0-9]+"' pyproject.toml | cut -d'"' -f2)
major=$(echo $current_version | cut -d'.' -f1)
minor=$(echo $current_version | cut -d'.' -f2)
patch=$(echo $current_version | cut -d'.' -f3)
new_patch=$((patch + 1))
new_version="$major.$minor.$new_patch"

echo "Incrementing version from $current_version to $new_version"
sed -i "s/version = \"$current_version\"/version = \"$new_version\"/" pyproject.toml

echo "Version updated successfully!"

echo "Deploying to git..."
git add .
git commit -m "Bump version to $new_version"
git push -u origin main

echo "Deployment complete!"