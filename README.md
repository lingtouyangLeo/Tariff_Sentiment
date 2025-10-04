# Tariff Sentiment Analysis Project

This project analyzes tariff-related sentiment in S&P 500 earnings call transcripts and its impact on stock returns using FinBERT and econometric models.

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
- ⚠️ **GPU Support**: NVIDIA GPU with CUDA recommended (25% faster FinBERT processing)
- Use the latest stable PyTorch version for security and performance

**Quick Verification:**

```bash
conda activate nlp
python --version      # Should be 3.11+ on macOS
python -c "import torch; print(torch.__version__)"  # Should be 2.2.0+
python -c "import torch; print(torch.cuda.is_available())"  # Should be True if GPU available
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
Tariff_Sentiment/
├── dataset/                          # Data files (input)
│   ├── events_20251001.csv          # Real earnings events data
│   ├── sp500_daily_returns.csv      # Stock price data
│   ├── F-F_Research_Data_5_Factors_2x3_daily.csv  # Fama-French factors
│   ├── sp500_summaries/             # Earnings call summaries (markdown)
│   └── sp500_transcripts/           # Earnings call transcripts (3,147 files)
│
├── src/                              # Source code (Python scripts)
│   ├── Tariff_Sentiment.py         # Step 1: Data processing (~2 hours)
│   ├── Generate_Plots.py           # Step 2: Visualization (~1 minute)
│   └── Regressions.py              # Step 3: Regression analysis (~30 seconds)
│
├── output/                           # Output files (generated, timestamped)
│   ├── YYYYMMDD_HHMMSS_tariff_data.pkl          # Main processed data
│   ├── YYYYMMDD_HHMMSS_tariff_data.csv          # CSV version (for inspection)
│   ├── YYYYMMDD_HHMMSS_transcripts_data.pkl     # Transcript data
│   ├── YYYYMMDD_HHMMSS_prices_data.pkl          # Price data
│   ├── YYYYMMDD_HHMMSS_factors_data.pkl         # Fama-French factors
│   ├── YYYYMMDD_HHMMSS_regression_results.txt   # Regression output
│   ├── YYYYMMDD_HHMMSS_regression_coefs.csv     # Coefficient table
│   ├── YYYYMMDD_HHMMSS_results.csv              # Final data (renamed variables)
│   ├── YYYYMMDD_HHMMSS_summary_report.txt       # Comprehensive report
│   └── plots/                       # Visualization outputs
│       ├── 8.1_time_series_sentiment.png
│       ├── 8.2_sector_heatmap.png
│       ├── 8.3_word_shifts.png
│       └── 8.4_sentiment_analysis.png
│
├── utils/                            # Utility scripts
│   ├── activate_nlp_env.sh         # Environment setup script
│   ├── edgar_download.py           # Data collection utilities
│   └── ...
│
├── .gitignore                        # Git ignore rules (excludes *.pkl, output files)
├── requirements.txt                  # Python dependencies
├── HOW_TO_RUN.md                    # Detailed usage guide
├── README.md                         # This file
├── LICENSE                           # MIT License
└── NLP_Project_1_Tariff_Sentiment_Analysis.pdf  # Project requirements
```

---

## 🚀 Quick Start

### Three-Step Workflow (Optimized for Fast Iteration)

The analysis is split into three independent scripts to avoid re-running expensive data processing when modifying regressions or plots.

#### Step 1: Data Processing (Run Once, ~2 hours)

**First time setup:**

```bash
conda activate nlp
python src/Tariff_Sentiment.py
```

This will:

- ✅ Load 3,147 earnings call transcripts
- ✅ Fetch EPS data from Yahoo Finance (~25 min, batched & cached)
- ✅ Extract tariff-related sentences using keyword + semantic matching
- ✅ Run FinBERT sentiment analysis (~54 min on GPU, 71 min on CPU)
- ✅ Calculate CAR (Cumulative Abnormal Returns) using market model
- ✅ Add control variables (size, momentum, after_hours, sector)
- ✅ **Save 5 processed data files to `output/` folder:**
  - `YYYYMMDD_HHMMSS_tariff_data.pkl` (main data for regressions)
  - `YYYYMMDD_HHMMSS_tariff_data.csv` (CSV for inspection)
  - `YYYYMMDD_HHMMSS_transcripts_data.pkl`
  - `YYYYMMDD_HHMMSS_prices_data.pkl`
  - `YYYYMMDD_HHMMSS_factors_data.pkl`

**⏱️ Total time:** ~1.5-2 hours (only need to run once!)

#### Step 2: Generate Visualizations (Can run multiple times, ~1 minute)

```bash
python src/Generate_Plots.py
```

This will:

- ✅ Automatically load the most recent `*_results.csv` file
- ✅ Generate 4 high-resolution plots
- ✅ Save plots to `output/plots/`

**⏱️ Total time:** ~1 minute

Generates:

1. **8.1_time_series_sentiment.png** - Time series of sentiment metrics by quarter
2. **8.2_sector_heatmap.png** - Sector-level sentiment heatmap
3. **8.3_word_shifts.png** - Word frequency comparison (negative vs positive events)
4. **8.4_sentiment_analysis.png** - Comprehensive sentiment distribution analysis

#### Step 3: Run Regressions (Can run multiple times, ~30 seconds)

```bash
python src/Regressions.py
```

This will:

- ✅ Automatically load the most recent `*_tariff_data.pkl` file
- ✅ Run 3 econometric specifications (Requirement 7):
  - Model 1: OLS with HC3 robust standard errors
  - Model 2: OLS with sector & quarter FE + firm-clustered SEs (main specification)
  - Model 3: PanelOLS with entity & time FE + two-way clustered SEs
- ✅ Apply variable renaming (Requirement 9)
- ✅ Apply outlier treatment - winsorization at 1%/99% (Requirement 11)
- ✅ Generate comprehensive summary report (Requirement 12)
- ✅ **Save 4 output files:**
  - `YYYYMMDD_HHMMSS_regression_results.txt` (full regression output)
  - `YYYYMMDD_HHMMSS_regression_coefs.csv` (coefficient table for Excel/LaTeX)
  - `YYYYMMDD_HHMMSS_results.csv` (final data with renamed variables)
  - `YYYYMMDD_HHMMSS_summary_report.txt` (comprehensive analysis report)

**⏱️ Total time:** ~30 seconds

---

### Typical Workflows

**Scenario 1: First-time complete run**

```bash
conda activate nlp
python src/Tariff_Sentiment.py    # Wait ~2 hours
python src/Generate_Plots.py       # Wait ~1 minute
python src/Regressions.py          # Wait ~30 seconds
```

**Scenario 2: Modify regression specification (fast iteration)**

```bash
# Edit src/Regressions.py to change regression models
python src/Regressions.py          # Only 30 seconds! No data reprocessing
```

**Scenario 3: Modify plot styles (fast iteration)**

```bash
# Edit src/Generate_Plots.py to change plot appearance
python src/Generate_Plots.py       # Only 1 minute! No data reprocessing
```

**Scenario 4: Update data processing logic**

```bash
# Edit src/Tariff_Sentiment.py
python src/Tariff_Sentiment.py    # Full rerun (~2 hours)
python src/Generate_Plots.py       # Update plots
python src/Regressions.py          # Update regressions
```

---

## 📊 Output Files

All output files are automatically timestamped (format: `YYYYMMDD_HHMMSS`) to prevent overwriting and track different runs.

### Step 1 Outputs (Tariff_Sentiment.py)

| File | Description | Size | Used By |
|------|-------------|------|---------|
| `*_tariff_data.pkl` | Main processed data (all variables) | ~50MB | Regressions.py |
| `*_tariff_data.csv` | CSV version for inspection | ~30MB | Manual review |
| `*_transcripts_data.pkl` | Original transcript text + metadata | ~100MB | Future analysis |
| `*_prices_data.pkl` | Daily returns data | ~20MB | Future analysis |
| `*_factors_data.pkl` | Fama-French 5-factor data | ~5MB | Future analysis |

**Key Variables in tariff_data:**

- **Event Info**: ticker, year, quarter, ann_date, conference_date
- **Tariff Metrics**: 
  - TariffSent_mean (average FinBERT sentiment of tariff sentences)
  - TariffMentions (count of tariff-related sentences)
  - TariffSent_shareNeg (share of negative sentences)
  - ForwardTone (sentiment of forward-looking tariff sentences)
- **Financial Data**: 
  - eps_actual, eps_consensus, eps_surprise
  - CAR (2-day cumulative abnormal return)
- **Controls**: size, momentum, after_hours, sector, quarter

### Step 2 Outputs (Generate_Plots.py)

Located in `output/plots/`:

1. **8.1_time_series_sentiment.png** (4-panel)
   - Tariff sentiment over time
   - Tariff mention frequency
   - Event counts per quarter
   - Share of negative sentiment

2. **8.2_sector_heatmap.png**
   - Average tariff sentiment by sector × quarter
   - Color-coded: Red (negative) → Green (positive)

3. **8.3_word_shifts.png**
   - Word frequency comparison
   - Top keywords in negative vs positive events

4. **8.4_sentiment_analysis.png** (4-panel)
   - Sentiment distribution histogram
   - Sentiment vs CAR scatter plot
   - Sentiment by sector box plot
   - Sentiment trend over time

### Step 3 Outputs (Regressions.py)

| File | Description |
|------|-------------|
| `*_regression_results.txt` | Full regression output for all 3 models |
| `*_regression_coefs.csv` | Coefficient table (easy import to Excel/LaTeX) |
| `*_results.csv` | Final dataset with renamed variables + winsorization |
| `*_summary_report.txt` | Comprehensive analysis report |

**Regression Models:**

- **Model 1**: OLS + HC3 robust SEs (baseline)
- **Model 2**: OLS + Sector & Quarter FE + Firm-clustered SEs ⭐ (main specification)
- **Model 3**: PanelOLS + Entity & Time FE + Two-way clustered SEs

**Variable Renaming (Requirement 9):**

| Original | Renamed |
|----------|---------|
| TariffSent_mean | TariffSent_mean_call_iq |
| TariffMentions | TariffMentions_iq |
| eps_surprise | Surprise_iq |
| CAR | CAR_iq |
| size | Size_iq |
| momentum | Momentum_iq |
| after_hours | AfterHours_iq |
| sector | Sector_i |
| quarter | Quarter_q |
| ticker | Ticker_i |

**Summary Report Contents:**

1. Dataset overview (N observations, date range, coverage)
2. Descriptive statistics (after winsorization)
3. Sample data preview
4. Regression results summary (key coefficients, R², significance)
5. Data quality assessment (missing values, outliers)
6. Interpretation guide (expected relationships, robustness)
7. Output file list

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

**Solution**: Make sure you're running from the project root (`Tariff_Sentiment/`)

```bash
cd c:\Users\leo\Desktop\Tariff_Sentiment    # Windows
# or
cd /path/to/Tariff_Sentiment                # macOS/Linux

python src/Tariff_Sentiment.py
```

### Issue: "No processed data files found" when running Regressions.py

**Error message:**
```
ERROR: No processed data files found!
Please run Tariff_Sentiment.py first to generate processed data.
```

**Solution**: Run data processing first

```bash
python src/Tariff_Sentiment.py  # Generate .pkl files (~2 hours)
python src/Regressions.py       # Then run regressions
```

### Issue: "CSV file not found" when generating plots

**Solution**: Run regressions first (which creates the final CSV)

```bash
python src/Tariff_Sentiment.py  # Step 1: Data processing
python src/Regressions.py       # Step 2: Creates results.csv
python src/Generate_Plots.py    # Step 3: Uses results.csv
```

### Issue: Import errors or missing packages

**Solution**: Re-install dependencies

```bash
conda activate nlp
pip install -r requirements.txt --upgrade
python -m spacy download en_core_web_sm
```

### Issue: spaCy model not found

**Solution**: Download the English model

```bash
conda activate nlp
python -m spacy download en_core_web_sm
```

### Issue: FinBERT running on CPU instead of GPU (slow)

**Check GPU availability:**

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None"}')"
```

**Solution 1**: Make sure you're using the `nlp` environment (not `base`)

```bash
conda activate nlp  # nlp environment has CUDA support
python src/Tariff_Sentiment.py
```

**Solution 2**: If GPU not available, processing will use CPU (25% slower but works)

- GPU: ~54 minutes for FinBERT
- CPU: ~71 minutes for FinBERT

### Issue: PanelOLS error in Model 3

**Error message:**
```
ValueError: The index on the time dimension must be either numeric or date-like
```

**Solution**: This has been fixed in the latest version of `Regressions.py`. The quarter variable is automatically converted to numeric format (e.g., "2024_Q1" → 20241).

If you still see this error, make sure you're using the latest code.

### Issue: Memory error during processing

**Solution**: Close other applications and try again. The full dataset requires ~8GB RAM.

If problem persists, process a subset of data:

```python
# Edit src/Tariff_Sentiment.py, line ~28
events_df = events_df.head(1000)  # Process only first 1000 events
```

### Issue: Yahoo Finance rate limiting (429 errors)

**Solution**: The code already includes rate limiting (0.15s delay per request). If you still see errors:

1. Wait 5-10 minutes before retrying
2. Check your internet connection
3. Yahoo Finance API is free but has usage limits

### Issue: Old output files cluttering the folder

**Solution**: It's safe to delete old timestamped files, but keep:

- Most recent `*_tariff_data.pkl` (needed by Regressions.py)
- Most recent `*_results.csv` (needed by Generate_Plots.py)
- Plots you want to keep

```bash
# Windows PowerShell
Remove-Item output\202510* -Exclude *203523*  # Keep only latest (example)

# macOS/Linux
rm output/202510* --exclude=*203523*  # Keep only latest (example)
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
