#!/bin/bash
# Setup script for TDX Tool development environment
# Supports: macOS, Linux, Windows (WSL)

set -e

echo "🚀 Setting up TDX Tool development environment..."
echo ""

# Check for conda
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Miniconda or Anaconda first."
    echo "   Visit: https://docs.conda.io/projects/miniconda/en/latest/"
    exit 1
fi

echo "✅ Conda found"

# Create environment
echo ""
echo "📦 Creating conda environment from environment.yml..."
conda env create -f environment.yml --force-reinstall -q

echo "✅ Environment created successfully"
echo ""
echo "⚙️  To activate the environment, run:"
echo "   conda activate tdx-dev"
echo ""
echo "📚 After activation, install the package in development mode:"
echo "   make install-dev"
echo ""
echo "🧪 To verify installation, run:"
echo "   make test"
echo ""
echo "💡 For more commands, run:"
echo "   make help"
