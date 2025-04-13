#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

print_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

# Function to increment version
increment_version() {
    local version=$1
    local increment_type=$2
    
    # Split version into major, minor, and patch
    IFS='.' read -r major minor patch <<< "$version"
    
    case $increment_type in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    print_warning "Virtual environment not activated. It's recommended to use a virtual environment."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for required tools
if ! command -v python3 &> /dev/null; then
    print_error "python3 is required but not installed."
    exit 1
fi

if ! command -v pip &> /dev/null; then
    print_error "pip is required but not installed."
    exit 1
fi

# Install required build tools if not present
print_message "Checking/Installing build requirements..."
pip install --quiet build twine

# Clean previous builds
print_message "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Version handling
print_message "Current version in pyproject.toml:"
current_version=$(grep "version = " pyproject.toml | cut -d'"' -f2)
echo "Current version: $current_version"

echo
echo "Choose version increment type:"
echo "1) Patch (${current_version} -> $(increment_version $current_version patch))"
echo "2) Minor (${current_version} -> $(increment_version $current_version minor))"
echo "3) Major (${current_version} -> $(increment_version $current_version major))"
echo "4) Manual version entry"
echo "5) Keep current version"
read -p "Select option (1-5): " version_choice

case $version_choice in
    1)
        new_version=$(increment_version $current_version patch)
        ;;
    2)
        new_version=$(increment_version $current_version minor)
        ;;
    3)
        new_version=$(increment_version $current_version major)
        ;;
    4)
        read -p "Enter new version number: " new_version
        ;;
    5)
        new_version=$current_version
        ;;
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

if [ "$new_version" != "$current_version" ]; then
    print_message "Updating to version $new_version"
    sed -i "s/version = \"$current_version\"/version = \"$new_version\"/" pyproject.toml
fi

# Build package
print_message "Building package..."
if ! python3 -m build; then
    print_error "Build failed!"
    exit 1
fi

# Verify .pypirc exists
if [ ! -f ~/.pypirc ]; then
    print_error ".pypirc file not found in home directory!"
    print_message "Please create ~/.pypirc with your PyPI token first."
    exit 1
fi

# Upload to PyPI
print_message "Uploading to PyPI..."
if ! python3 -m twine upload dist/*; then
    print_error "Upload failed!"
    exit 1
fi

print_message "Package successfully published to PyPI! 🎉" 