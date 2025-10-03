# Tariff Sentiment Analysis Project

## ⚠️ IMPORTANT: Security & Compatibility Requirements

### Python Version Requirements

**macOS Users (Apple Silicon & Intel):**

- ✅ **Python 3.11+ is REQUIRED**
- ❌ **Python 3.10 and below are NOT supported**
- **Reason**: Best compatibility with PyTorch and modern ML libraries
- Python 3.11+ provides better performance and security

**Windows/Linux Users:**

- ✅ Python 3.10+ is acceptable
- ✅ Python 3.11+ recommended for best compatibility

### PyTorch Version Requirement

- ✅ **`torch>=2.2.0` (currently using latest available: 2.2.2)**
- ⚠️ **Note**: PyTorch 2.6 is not yet released. When available, upgrade immediately
- Use the latest stable PyTorch version for security and performance

**Quick Verification:**

```bash
conda activate nlp
python --version      # Should be 3.11+ on macOS
python -c "import torch; print(torch.__version__)"  # Should be 2.2.0+
```

---

## 🛠️ Environment Setup

### Quick Setup (One Command)

For first-time setup or deployment on a new machine:

```bash
cd /path/to/NLP/HW/HW1
source utils/activate_nlp_env.sh
```

This intelligent script will:

- ✅ Check if `nlp` conda environment exists
- ✅ Create environment if needed (Python 3.11 on macOS, 3.10+ on Windows/Linux)
- ✅ Install all dependencies from `requirements.txt`
- ✅ Download spaCy English model (`en_core_web_sm`)
- ✅ Verify all packages are correctly installed
- ✅ Activate the environment

### Manual Setup (Alternative)

If you prefer manual setup:

```bash
# Create conda environment
# For macOS: Python 3.11+ is REQUIRED
conda create -n nlp python=3.11 -y

# For Windows/Linux: Python 3.10+ works, but 3.11+ recommended
# conda create -n nlp python=3.10 -y

conda activate nlp

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Required Dependencies

- **Core**: pandas, numpy, scikit-learn, scipy
- **Deep Learning & NLP**: torch, transformers, sentence-transformers, spacy
- **Statistics**: statsmodels
- **Finance**: yfinance
- **Visualization**: matplotlib, seaborn

See `requirements.txt` for complete list with versions.

---

## 📁 Project Structure

```
HW1/
├── dataset/                          # Data files (input)
│   ├── events_20251001.csv          # Real earnings events data
│   ├── sp500_daily_returns.csv      # Stock price data
│   ├── F-F_Research_Data_5_Factors_2x3_daily.csv  # Fama-French factors
│   ├── sp500_summaries/             # Earnings call summaries
│   └── sp500_transcripts/           # Earnings call transcripts
│
├── src/                              # Source code (Python scripts)
│   ├── Tariff_Sentiment.py         # Main analysis script
│   └── Generate_Plots.py           # Visualization script
│
├── output/                           # Output files (generated)
│   ├── YYYYMMDD_HHMMSS_results.csv # Analysis results (timestamped)
│   └── plots/                       # Visualization outputs
│       ├── 8.1_time_series_sentiment.png
│       ├── 8.2_sector_heatmap.png
│       ├── 8.3_word_shifts.png
│       └── 8.4_sentiment_analysis.png
│
├── utils/                            # Utility scripts
├── requirements.txt                  # Python dependencies
├── README.md                         # This file
└── NLP_Project_1_Tariff_Sentiment_Analysis.pdf  # Project requirements
```

---

## 🚀 Quick Start

### Step 1: Setup Environment

**First time or new machine:**

```bash
source utils/activate_nlp_env.sh
```

**Subsequent uses:**

```bash
conda activate nlp
```

### Step 2: Verify Setup (Recommended)

```bash
python -c "
import pandas, numpy, transformers, torch
import sentence_transformers, statsmodels, spacy, yfinance
import matplotlib, seaborn
nlp = spacy.load('en_core_web_sm')
print('✓ All packages installed successfully!')
"
```

### Step 3: Run Main Analysis

```bash
python src/Tariff_Sentiment.py
```

This will:

- Load all data from `dataset/`
- Process transcripts and calculate sentiment
- Generate CAR using market model
- Run simple regression
- Save results to `output/YYYYMMDD_HHMMSS_results.csv` (timestamped)
- ⏱️ Takes 15-30 minutes

### Step 4: Generate Visualizations

```bash
python src/Generate_Plots.py
```

This will:

- Find and load the most recent `*_results.csv` file
- Generate 4 high-resolution plots
- Save plots to `output/plots/`
- ⏱️ Takes <1 minute

---

## 📊 Output Files

### CSV Results (`output/YYYYMMDD_HHMMSS_results.csv`)

**File naming**: Automatically timestamped with format `20251002_143022_results.csv`

- Makes it easy to track different runs
- Prevents overwriting previous results
- Visualization script automatically finds the latest file

Contains all analysis results with columns:

- **Event Info**: ticker, year, quarter, conference_date
- **Tariff Metrics**: TariffSent_mean, TariffMentions, tariff_sentences
- **Financial Data**: eps_actual, eps_consensus, eps_surprise, CAR
- **Controls**: size, momentum, after_hours, sector

### Plots (`output/plots/`)

1. **8.1_time_series_sentiment.png**

   - 4-panel time series analysis
   - Sentiment, mentions, event counts, negativity rate

2. **8.2_sector_heatmap.png**

   - Heatmap of sentiment by sector and quarter
   - Color-coded: Red (negative) → Green (positive)

3. **8.3_word_shifts.png**

   - Word frequency comparison
   - Negative vs positive events

4. **8.4_sentiment_analysis.png**
   - 4-panel comprehensive analysis
   - Distribution, scatter, box plot, time trend

---


## 🐛 Troubleshooting

### Issue: Environment setup fails

**Solution**: Make sure Anaconda or Miniconda is installed

```bash
# Check conda installation
conda --version

# If not found, download from:
# https://www.anaconda.com/download
```

### Issue: "File not found" error

**Solution**: Make sure you're running from the project root (`HW1/`)

```bash
cd /path/to/NLP/HW/HW1
python src/Tariff_Sentiment.py
```

### Issue: "CSV file not found" when generating plots

**Solution**: Run main analysis first

```bash
python src/Tariff_Sentiment.py  # Generate CSV
python src/Generate_Plots.py     # Then plots
```

### Issue: Import errors or missing packages

**Solution**: Re-run the setup script

```bash
source utils/activate_nlp_env.sh
```

Or manually install:

```bash
conda activate nlp
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Issue: spaCy model not found

**Solution**: Download the English model

```bash
conda activate nlp
python -m spacy download en_core_web_sm
```

---

## 📚 Dependencies

All dependencies are managed through `requirements.txt`:

**Core Data Science:**

- pandas==2.3.1
- numpy==1.26.4
- scikit-learn==1.7.1
- scipy==1.15.3

**Deep Learning & NLP:**

- torch==2.2.2
- transformers==4.56.2 (FinBERT)
- sentence-transformers==5.1.1
- spacy==3.8.7
- en_core_web_sm (spaCy model)

**Statistics:**

- statsmodels==0.14.5

**Finance:**

- yfinance>=0.2.66

**Visualization:**

- matplotlib>=3.10.0
- seaborn>=0.13.0

Install all at once:

```bash
pip install -r requirements.txt
```

---

---

## 📧 Notes

- All input data stays in `dataset/` (never modified)
- All outputs go to `output/` (can be deleted and regenerated)
- All Python code in `src/` (clean separation)
- Use relative paths for portability

---
