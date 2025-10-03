#!/bin/bash
# =============================================================================
# NLP Environment Setup and Activation Script
# =============================================================================
# Features:
#   1. Check if 'nlp' conda virtual environment exists
#   2. If not exists, automatically create and install all dependencies
#   3. If exists, directly activate it
#   4. Verify all required packages are installed
#
# Usage:
#   source utils/activate_nlp_env.sh
#
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}NLP Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Initialize conda for shell
if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]; then
    source /opt/anaconda3/etc/profile.d/conda.sh
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
    echo -e "${RED}Error: Cannot find conda installation${NC}"
    echo -e "${YELLOW}Please ensure Anaconda or Miniconda is installed${NC}"
    return 1
fi

# Check if nlp environment exists
echo -e "\n${YELLOW}Checking for nlp virtual environment...${NC}"
if conda env list | grep -q "^nlp "; then
    echo -e "${GREEN}✓ Found nlp environment${NC}"
    ENV_EXISTS=true
else
    echo -e "${YELLOW}✗ nlp environment not found, will create new one${NC}"
    ENV_EXISTS=false
fi

# Create environment if it doesn't exist
if [ "$ENV_EXISTS" = false ]; then
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}Creating nlp Virtual Environment${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    # Detect OS and set Python version accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS: Python 3.11+ required for PyTorch 2.6+ security compliance
        PYTHON_VERSION="3.11"
        echo -e "${YELLOW}Detected macOS: Using Python 3.11 (required for PyTorch security)${NC}"
    else
        # Linux/Windows: Python 3.10 acceptable but 3.11 recommended
        PYTHON_VERSION="3.11"
        echo -e "${YELLOW}Using Python 3.11 (recommended for best compatibility)${NC}"
    fi
    
    # Create conda environment
    echo -e "${YELLOW}Creating conda environment (Python $PYTHON_VERSION)...${NC}"
    conda create -n nlp python=$PYTHON_VERSION -y
    
    # Activate the environment
    echo -e "${YELLOW}Activating nlp environment...${NC}"
    conda activate nlp
    
    # Get the directory of this script
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
    
    # Install requirements from requirements.txt
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        echo -e "\n${YELLOW}Installing dependencies (from requirements.txt)...${NC}"
        pip install -r "$PROJECT_ROOT/requirements.txt"
    else
        echo -e "${RED}Warning: Cannot find requirements.txt${NC}"
        echo -e "${YELLOW}Installing required packages manually...${NC}"
        pip install pandas numpy scikit-learn torch transformers sentence-transformers \
                    statsmodels spacy yfinance matplotlib seaborn
    fi
    
    # Download spaCy English model
    echo -e "\n${YELLOW}Downloading spaCy English model...${NC}"
    python -m spacy download en_core_web_sm
    
    echo -e "\n${GREEN}✓ Environment created successfully!${NC}"
else
    # Activate existing environment
    echo -e "${YELLOW}Activating existing nlp environment...${NC}"
    conda activate nlp
fi

# Verify installation
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Verifying Environment Configuration${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "${YELLOW}Python interpreter:${NC} $(which python)"
echo -e "${YELLOW}Python version:${NC} $(python --version)"

# Check all required packages
echo -e "\n${YELLOW}Checking installed packages:${NC}"

check_package() {
    local package=$1
    local import_name=$2
    if python -c "import $import_name" 2>/dev/null; then
        local version=$(python -c "import $import_name; print($import_name.__version__)" 2>/dev/null)
        echo -e "  ${GREEN}✓${NC} $package ${BLUE}($version)${NC}"
        return 0
    else
        echo -e "  ${RED}✗${NC} $package ${RED}(not installed)${NC}"
        return 1
    fi
}

ALL_OK=true

check_package "pandas" "pandas" || ALL_OK=false
check_package "numpy" "numpy" || ALL_OK=false
check_package "transformers" "transformers" || ALL_OK=false
check_package "torch" "torch" || ALL_OK=false
check_package "scikit-learn" "sklearn" || ALL_OK=false
check_package "sentence-transformers" "sentence_transformers" || ALL_OK=false
check_package "statsmodels" "statsmodels" || ALL_OK=false
check_package "spacy" "spacy" || ALL_OK=false
check_package "yfinance" "yfinance" || ALL_OK=false
check_package "matplotlib" "matplotlib" || ALL_OK=false
check_package "seaborn" "seaborn" || ALL_OK=false

# Check spaCy model
echo -e "\n${YELLOW}Checking spaCy English model:${NC}"
if python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} en_core_web_sm ${GREEN}(installed)${NC}"
else
    echo -e "  ${RED}✗${NC} en_core_web_sm ${RED}(not installed)${NC}"
    echo -e "${YELLOW}Downloading spaCy model...${NC}"
    python -m spacy download en_core_web_sm
    ALL_OK=false
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✓ All dependencies installed successfully!${NC}"
else
    echo -e "${YELLOW}⚠ Some packages may need reinstallation${NC}"
    echo -e "${YELLOW}Please run: pip install -r requirements.txt${NC}"
fi
echo -e "${BLUE}========================================${NC}"

echo -e "\n${GREEN}Environment activated!${NC}"
echo -e "${YELLOW}Usage examples:${NC}"
echo -e "  cd HW/HW1"
echo -e "  python src/Tariff_Sentiment.py"
echo -e "  python src/Generate_Plots.py"
echo -e "\n${YELLOW}To deactivate:${NC}"
echo -e "  conda deactivate"
echo ""