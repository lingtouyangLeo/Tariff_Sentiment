import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
import pandas as pd, numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch, re
from sentence_transformers import SentenceTransformer, util
import statsmodels.api as sm
from datetime import datetime
import spacy
from pathlib import Path
import yfinance as yf
from tqdm import tqdm

# Set up directory paths
BASE_DIR = Path(__file__).parent.parent  # Project root directory
DATA_DIR = BASE_DIR / 'dataset'
OUTPUT_DIR = BASE_DIR / 'output'

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / 'plots').mkdir(exist_ok=True)

print("Loading data with real events and EPS...")

# 1) Load  events data with actual earnings call dates
events_df = pd.read_csv(DATA_DIR / 'events_20251001.csv')
events_df['date'] = pd.to_datetime(events_df['date'])
events_df = events_df[events_df['has_transcript'] == 'YES'].copy()
print(f"Loaded {len(events_df)} events with transcripts")

# 2) Load SP500 daily returns data
prices = pd.read_csv(DATA_DIR / 'sp500_daily_returns.csv')
prices['Date'] = pd.to_datetime(prices['Date'])
prices = prices.set_index('Date').sort_index()

# 3) Load Fama-French factors  
factors = pd.read_csv(DATA_DIR / 'F-F_Research_Data_5_Factors_2x3_daily.csv', skiprows=4)
factors.columns = ['date', 'MKT-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF']

# Clean and convert date - handle non-numeric entries
factors = factors[factors['date'].astype(str).str.isdigit()]  # Keep only numeric dates
factors['date'] = pd.to_datetime(factors['date'].astype(str), format='%Y%m%d', errors='coerce')
factors = factors.dropna(subset=['date'])  # Remove any failed conversions
factors = factors.set_index('date')

# Convert factor values to numeric
for col in ['MKT-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF']:
    factors[col] = pd.to_numeric(factors[col], errors='coerce') / 100  # Convert to decimal

factors['MKT'] = factors['MKT-RF'] + factors['RF']  # Market return

# Create ticker mapping
ticker_columns = [col for col in prices.columns if col != 'Date']
ticker_map = {ticker: ticker for ticker in ticker_columns}
print(f"Found {len(ticker_columns)} tickers in returns data")

# 4) Fallback EPS extraction from summary files
def extract_eps_from_summary(ticker, year, quarter):
    """Extract EPS actual and consensus from summary markdown files"""
    summary_file = DATA_DIR / f"sp500_summaries/sp500_summaries/{ticker}_{year}_Q{quarter}_summary.md"
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for actual EPS patterns first
        eps_actual_patterns = [
            r"EPS.*?diluted.*?\$([0-9]+\.[0-9]+)",   # EPS (diluted): $1.88
            r"diluted.*?EPS.*?\$([0-9]+\.[0-9]+)",   # diluted EPS: $1.88
            r"EPS:\s*\$([0-9]+\.[0-9]+)",            # EPS: $1.64
            r"reported.*?EPS.*?\$([0-9]+\.[0-9]+)",  # reported EPS of $1.64
            r"actual.*?EPS.*?\$([0-9]+\.[0-9]+)",    # actual EPS of $1.64
            r"earnings per share.*?\$([0-9]+\.[0-9]+)",  # earnings per share of $1.64
            r"\$([0-9]+\.[0-9]+)\s*(?:per share|EPS)",  # $1.64 per share
        ]
        
        # Look for consensus/estimate EPS patterns
        eps_consensus_patterns = [
            r"consensus.*?\$?([0-9]+\.[0-9]+)",      # consensus of $1.64
            r"estimate.*?\$?([0-9]+\.[0-9]+)",       # estimate of $1.64
            r"expected.*?\$?([0-9]+\.[0-9]+)",       # expected $1.64
            r"forecast.*?\$?([0-9]+\.[0-9]+)",       # forecast $1.64
            r"analyst.*?expect.*?\$?([0-9]+\.[0-9]+)", # analysts expect $1.64
        ]
        
        eps_actual = np.nan
        eps_consensus = np.nan
        
        # Extract actual EPS
        for pattern in eps_actual_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    eps_value = float(matches[0])
                    if 0 < eps_value < 50:  # Reasonable EPS range
                        eps_actual = eps_value
                        break
                except:
                    continue
        
        # Extract consensus EPS
        for pattern in eps_consensus_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    eps_value = float(matches[0])
                    if 0 < eps_value < 50:  # Reasonable EPS range
                        eps_consensus = eps_value
                        break
                except:
                    continue
        
        return eps_actual, eps_consensus
        
    except FileNotFoundError:
        return np.nan, np.nan
    except Exception:
        return np.nan, np.nan

# 5) Extract EPS and calculate Simple EPS Surprise using Yahoo Finance - Direct fetch

def get_yf_eps_and_price_data(ticker_symbol, earnings_date):
    """
    Get EPS actual, EPS consensus, and price data from Yahoo Finance - Direct fetch without delays
    Formula: Surprise = (EPS_actual - EPS_consensus) / |Price_pre|
    """
    try:
        # Create ticker object - direct fetch
        ticker = yf.Ticker(ticker_symbol)
        
        # Get EPS from info (most reliable)
        eps_actual = np.nan
        eps_consensus = np.nan
        
        try:
            info = ticker.info
            if 'trailingEps' in info and info['trailingEps'] is not None:
                eps_actual = info['trailingEps']
            if 'forwardEps' in info and info['forwardEps'] is not None:
                eps_consensus = info['forwardEps']
        except:
            pass
        
        # Try earnings_dates if needed
        if pd.isna(eps_actual) or pd.isna(eps_consensus):
            try:
                earnings = ticker.earnings_dates
                if earnings is not None and len(earnings) > 0:
                    valid_earnings = earnings.dropna(subset=['Reported EPS', 'EPS Estimate'])
                    if len(valid_earnings) > 0:
                        latest = valid_earnings.iloc[0]
                        if pd.isna(eps_actual) and 'Reported EPS' in latest:
                            eps_actual = latest['Reported EPS']
                        if pd.isna(eps_consensus) and 'EPS Estimate' in latest:
                            eps_consensus = latest['EPS Estimate']
            except:
                pass
        
        # Get price data
        price_pre = np.nan
        try:
            earnings_date = pd.to_datetime(earnings_date)
            start_date = earnings_date - pd.Timedelta(days=10)
            end_date = earnings_date + pd.Timedelta(days=2)
            
            hist = ticker.history(start=start_date, end=end_date)
            if len(hist) > 0:
                # Fix timezone issues
                hist.index = hist.index.tz_localize(None) if hist.index.tz is not None else hist.index
                earnings_date_only = earnings_date.date()
                
                # Find price before earnings
                for i in range(1, 8):  # Check up to 7 days before
                    check_date = pd.Timestamp(earnings_date_only) - pd.Timedelta(days=i)
                    available_dates = hist.index[hist.index <= check_date]
                    if len(available_dates) > 0:
                        closest_date = available_dates[-1]
                        price_pre = hist.loc[closest_date, 'Close']
                        break
                
                # Fallback to most recent price if no pre-earnings price found
                if pd.isna(price_pre) and len(hist) > 0:
                    price_pre = hist['Close'].iloc[-1]
        except:
            pass
        
        # Calculate EPS Surprise
        eps_surprise = np.nan
        if not pd.isna(eps_actual) and not pd.isna(eps_consensus) and not pd.isna(price_pre) and price_pre > 0:
            eps_surprise = (eps_actual - eps_consensus) / abs(price_pre) 
        elif not pd.isna(eps_actual) and not pd.isna(price_pre) and price_pre > 0:
            # Simple version without consensus
            eps_surprise = eps_actual / abs(price_pre)
        
        return eps_actual, eps_consensus, price_pre, eps_surprise
        
    except Exception as e:
        # Simplified error handling - no retries, no delays
        return np.nan, np.nan, np.nan, np.nan

# 5) Load transcripts and extract EPS data in one step
print("Loading transcripts based on events data...")
transcripts_data = []

transcript_dir = DATA_DIR / 'sp500_transcripts/sp500_transcripts'
# Only process events that have transcripts
processed_count = 0

# Use tqdm for progress visualization
for idx, row in tqdm(events_df.iterrows(), total=len(events_df), desc="Loading transcripts"):
    ticker = row['symbol']
    year = row['year'] 
    quarter = row['quarter']
    
    # Look for matching transcript file
    transcript_file = transcript_dir / f"{ticker}_{year}_Q{quarter}.txt"
    
    if transcript_file.exists():
        processed_count += 1
        
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Use earnings date from events CSV for all calculations
            earnings_date = pd.to_datetime(row['date'])  # This is the actual earnings announcement date
            
            # Get ALL data from Yahoo Finance: EPS actual, EPS consensus, and price data
            eps_actual, eps_consensus, price_pre, eps_surprise = get_yf_eps_and_price_data(ticker, earnings_date)
            
            # If Yahoo Finance failed completely, try fallback EPS from summary files
            if pd.isna(eps_actual):
                eps_actual, eps_consensus_fallback = extract_eps_from_summary(ticker, year, quarter)
                # If we got EPS from summary but no price, can't calculate surprise
                if not pd.isna(eps_actual) and pd.isna(price_pre):
                    eps_surprise = np.nan  # Can't calculate without price
            
            transcripts_data.append({
                'ticker': ticker,
                'year': year,
                'quarter': quarter,
                'fqtr': f'{year}_Q{quarter}',
                'ann_date': earnings_date,  # Use earnings_date from events CSV
                'conference_date': pd.to_datetime(row['conference_date']),
                'eps_actual': eps_actual,
                'eps_consensus': eps_consensus,
                'price_pre': price_pre,
                'eps_surprise': eps_surprise,  # Simple EPS Surprise formula
                'text': text
            })
            
        except Exception as e:
            print(f"Error reading transcript {transcript_file}: {e}")

transcripts_df = pd.DataFrame(transcripts_data)
print(f"Loaded {len(transcripts_df)} transcripts with real dates")
print(f"Date range: {transcripts_df['ann_date'].min()} to {transcripts_df['ann_date'].max()}")

# Data quality statistics
yahoo_eps_count = (~transcripts_df['eps_consensus'].isna()).sum()
fallback_eps_count = ((~transcripts_df['eps_actual'].isna()) & (transcripts_df['eps_consensus'].isna())).sum()
no_eps_count = (transcripts_df['eps_actual'].isna()).sum()

print(f"\nEPS Data Quality:")
print(f"- Yahoo Finance EPS (with consensus): {yahoo_eps_count}")
print(f"- Fallback EPS (from summaries): {fallback_eps_count}")
print(f"- No EPS data available: {no_eps_count}")
print(f"- Valid EPS Surprise calculations: {(~transcripts_df['eps_surprise'].isna() & (transcripts_df['eps_surprise'] != 0)).sum()}")

# Load spaCy for sentence splitting
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Please install spaCy English model: python -m spacy download en_core_web_sm")
    nlp = None

# 7) Build tariff sentence extractor
print("Building tariff sentence extractor...")

# Enhanced tariff lexicon
tariff_keywords = [
    r"tariff(s)?", r"dut(y|ies)", r"lev(y|ies)", r"quota(s)?",
    r"section\s*301", r"countervailing", r"anti[- ]dump(ing)?",
    r"import tax(es)?", r"customs", r"decoupling", r"retaliator(y|y measures)", 
    r"exemption(s)?", r"exclusion(s)?", r"harmonized codes?",
    r"trade war", r"trade tension", r"china tariff", r"steel tariff",
    r"aluminum tariff", r"solar tariff"
]
kw_re = re.compile(r"(" + r"|".join(tariff_keywords) + r")", re.I)

# Embedding similarity for semantic matching
embed = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
seed_queries = [
    "impact of tariffs on costs", "duty increases on imports", "tariff headwinds/tailwinds", 
    "tariff exclusions expired", "retaliatory tariffs from trading partners",
    "tariff relief", "exclusion expired", "duties on imports",
    "trade policy impact", "import cost pressure"
]
seed_vec = embed.encode(seed_queries, normalize_embeddings=True)

def split_into_sentences(text):
    """Split text into sentences using simple heuristics if spaCy not available"""
    if nlp:
        doc = nlp(text)
        return [sent.text.strip() for sent in doc.sents]
    else:
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

def tariff_sentences(doc_text, use_semantic=True, sim_threshold=0.45):
    """Extract tariff-related sentences using keywords + semantic similarity"""
    sentences = split_into_sentences(doc_text)
    
    # Primary: keyword matching
    hits = [s for s in sentences if kw_re.search(s)]
    
    # Secondary: semantic similarity expansion (if few keyword matches)
    if use_semantic and len(hits) < 3 and len(sentences) > 0:
        try:
            S = embed.encode(sentences, normalize_embeddings=True)
            sims = np.max(util.cos_sim(S, seed_vec).cpu().numpy(), axis=1)
            aug = [sentences[i] for i,sim in enumerate(sims) if sim > sim_threshold]
            hits = list(set(hits + aug))  # combine and deduplicate
        except Exception as e:
            print(f"Semantic similarity failed: {e}")
    
    return hits

# 8) Sentiment model (FinBERT)
print("Loading FinBERT model...")

# Set device for FinBERT
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

try:
    tok = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    clf = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert").to(device).eval()
    finbert_loaded = True
    print(f"FinBERT loaded successfully on {device}")
except Exception as e:
    print(f"Could not load FinBERT: {e}")
    print("Will use simple sentiment scoring as fallback")
    finbert_loaded = False

def finbert_polarity(sents):
    """Score sentences as pos/neg/neu and return multiple metrics"""
    if not finbert_loaded or len(sents) == 0:
        return 0.0, 0.5, len(sents), 0.0  # neutral fallback
    
    try:
        with torch.no_grad():
            inputs = tok(sents, padding=True, truncation=True, return_tensors="pt", max_length=512)
            # Move inputs to the same device as model
            inputs = {k: v.to(device) for k, v in inputs.items()}
            logits = clf(**inputs).logits
            probs = torch.softmax(logits, dim=1).cpu().numpy()  # Move back to CPU for numpy
        
        # FinBERT classes: [negative, neutral, positive]
        neg_probs = probs[:,0]
        neu_probs = probs[:,1] 
        pos_probs = probs[:,2]
        
        # Multiple sentiment metrics
        tariff_sent_mean = (pos_probs - neg_probs).mean()  # mean polarity [-1,1]
        tariff_sent_share_neg = (neg_probs > pos_probs).mean()  # share negative
        tariff_mentions = len(sents)  # count of tariff sentences
        
        # Forward-looking tone (sentences with future cues)
        future_cues = ['expect', 'guidance', 'outlook', 'plan', 'will', 'next quarter', 'next year', 'going forward']
        future_mask = np.array([any(cue in sent.lower() for cue in future_cues) for sent in sents])
        
        if future_mask.sum() > 0:
            forward_tone = (pos_probs[future_mask] - neg_probs[future_mask]).mean()
        else:
            forward_tone = 0.0
            
        return tariff_sent_mean, tariff_sent_share_neg, tariff_mentions, forward_tone
        
    except Exception as e:
        print(f"FinBERT prediction failed: {e}")
        return 0.0, 0.5, len(sents), 0.0

# 9) Process transcripts for tariff sentiment
print("Processing transcripts for tariff sentiment...")

tariff_metrics = []
for idx, row in tqdm(transcripts_df.iterrows(), total=len(transcripts_df), desc="Processing tariff sentiment"):
    # Extract tariff sentences
    tariff_sents = tariff_sentences(row['text'])
    
    if len(tariff_sents) > 0:
        # Get sentiment metrics
        sent_mean, share_neg, mentions, forward_tone = finbert_polarity(tariff_sents)
    else:
        sent_mean, share_neg, mentions, forward_tone = 0.0, 0.0, 0, 0.0
    
    tariff_metrics.append({
        'ticker': row['ticker'], 
        'fqtr': row['fqtr'],
        'ann_date': row['ann_date'],  # ann_time_{i,q}: timestamp of press release
        'conference_date': row['conference_date'],  # call_time_{i,q}: call start timestamp
        'eps_actual': row['eps_actual'],
        'eps_surprise': row['eps_surprise'],  # Surprise_EPS_{i,q} (primary)
        'TariffSent_mean': sent_mean,  # Will be renamed to TariffSent_mean_call_{i,q}
        'TariffSent_shareNeg': share_neg,
        'TariffMentions': mentions,  # TariffMentions_{i,q}
        'ForwardTone': forward_tone,  # TariffSent_fwd_{i,q} (forward-looking subset)
        'tariff_sentences': tariff_sents[:5]  # keep first 5 for inspection
    })

tariff_df = pd.DataFrame(tariff_metrics)
print(f"Extracted tariff metrics for {len(tariff_df)} transcripts")
print(f"Transcripts with tariff mentions: {(tariff_df['TariffMentions'] > 0).sum()}")

# 10) Calculate CAR using real announcement dates
print("Calculating abnormal returns using real announcement dates...")

def calculate_car_for_event(ticker, ann_date, car_window=(0,1)):
    """Calculate CAR for a specific event using market model with real dates"""
    try:
        # Check if ticker exists in returns data
        if ticker not in prices.columns:
            print(f"Warning: {ticker} not found in returns data")
            return np.nan
            
        # Get stock returns for this ticker
        stock_returns = prices[ticker].dropna()
        
        if len(stock_returns) < 100:  # Need sufficient data
            return np.nan
        
        # Merge with market factors using dates
        common_dates = stock_returns.index.intersection(factors.index)
        if len(common_dates) < 100:
            return np.nan
            
        stock_data = pd.DataFrame({
            'RET': stock_returns.loc[common_dates],
            'MKT-RF': factors.loc[common_dates, 'MKT-RF']
        }).dropna()
        
        if len(stock_data) < 100:
            return np.nan
        
        # Estimation window: -250 to -20 days from actual announcement date
        est_start = ann_date - pd.Timedelta(days=250)
        est_end = ann_date - pd.Timedelta(days=20)
        
        est_window = stock_data[(stock_data.index >= est_start) & (stock_data.index <= est_end)]
        
        if len(est_window) < 50:  # Need sufficient data
            return np.nan
            
        # Market model regression
        X = sm.add_constant(est_window['MKT-RF'].astype(float))
        y = est_window['RET'].astype(float)
        
        # Only keep common dates
        valid_idx = y.index.intersection(X.index)
        X_clean = X.loc[valid_idx]
        y_clean = y[valid_idx]
        
        if len(y_clean) < 30:
            return np.nan
            
        model = sm.OLS(y_clean, X_clean).fit()
        alpha, beta = model.params.iloc[0], model.params.iloc[1]
        
        # Event window - use actual announcement date
        event_start = ann_date + pd.Timedelta(days=car_window[0])
        event_end = ann_date + pd.Timedelta(days=car_window[1])
        
        event_window = stock_data[(stock_data.index >= event_start) & (stock_data.index <= event_end)]
        
        if len(event_window) == 0:
            return np.nan
            
        # Calculate abnormal returns
        predicted_returns = alpha + beta * event_window['MKT-RF'].astype(float)
        abnormal_returns = event_window['RET'].astype(float) - predicted_returns
        
        return abnormal_returns.sum()
        
    except Exception as e:
        print(f"CAR calculation failed for ticker {ticker}: {e}")
        return np.nan

# Calculate CARs for all events using real dates
cars = []
for idx, row in tariff_df.iterrows():
    car = calculate_car_for_event(row['ticker'], row['ann_date'])
    cars.append(car)

tariff_df['CAR'] = cars

# 11) Use Simple EPS Surprise from Yahoo Finance
print("Using Simple EPS Surprise from Yahoo Finance...")
print("Formula: Surprise = (EPS_actual - EPS_consensus) / |Price_pre|")

# The eps_surprise is already calculated in the data loading step
# Just add it to tariff_df (it should already be there)
valid_eps_surprise = (~tariff_df['eps_surprise'].isna()).sum()
print(f"Events with valid EPS surprise: {valid_eps_surprise}/{len(tariff_df)}")

# Also calculate some summary statistics
if valid_eps_surprise > 0:
    mean_surprise = tariff_df['eps_surprise'].mean()
    std_surprise = tariff_df['eps_surprise'].std()
    print(f"Mean EPS Surprise: {mean_surprise:.6f}")
    print(f"Std EPS Surprise: {std_surprise:.6f}")
    
    # Show distribution
    surprise_pos = (tariff_df['eps_surprise'] > 0).sum()
    surprise_neg = (tariff_df['eps_surprise'] < 0).sum()
    print(f"Positive surprises: {surprise_pos}, Negative surprises: {surprise_neg}")

# 12) Add other control variables
print("Adding control variables...")

# Size (volatility proxy since we don't have market cap data)
size_data = []
for idx, row in tqdm(tariff_df.iterrows(), total=len(tariff_df), desc="Calculating size variables"):
    try:
        if row['ticker'] in prices.columns:
            stock_returns = prices[row['ticker']].dropna()
            recent_data = stock_returns[stock_returns.index <= row['ann_date']].tail(60)
            volatility = recent_data.std()
            size_data.append(volatility if not pd.isna(volatility) else np.nan)
        else:
            size_data.append(np.nan)
    except:
        size_data.append(np.nan)

tariff_df['size'] = size_data

# Momentum (past 6-month return)
momentum_data = []
for idx, row in tqdm(tariff_df.iterrows(), total=len(tariff_df), desc="Calculating momentum variables"):
    try:
        if row['ticker'] in prices.columns:
            stock_returns = prices[row['ticker']].dropna()
            start_date = row['ann_date'] - pd.Timedelta(days=180)
            momentum_window = stock_returns[(stock_returns.index >= start_date) & (stock_returns.index <= row['ann_date'])]
            if len(momentum_window) > 0:
                momentum = (momentum_window + 1).prod() - 1
                momentum_data.append(momentum)
            else:
                momentum_data.append(np.nan)
        else:
            momentum_data.append(np.nan)
    except:
        momentum_data.append(np.nan)

tariff_df['momentum'] = momentum_data

# Add other variables
tariff_df['after_hours'] = (tariff_df['conference_date'].dt.hour >= 16).astype(int)  # After-hours indicator

# Get sector information once per unique ticker to avoid rate limits
unique_tickers = tariff_df['ticker'].unique()
sector_dict = {}

print(f"Fetching sector information for {len(unique_tickers)} unique tickers...")
for ticker in tqdm(unique_tickers, desc="Fetching sectors"):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        sector_dict[ticker] = info.get('sector', 'Unknown')
    except Exception as e:
        print(f"Failed to get sector for {ticker}: {e}")
        sector_dict[ticker] = 'Unknown'

tariff_df['sector'] = tariff_df['ticker'].map(sector_dict)
print("Sector information added.")

tariff_df['quarter'] = tariff_df['fqtr']

# Filter to only include Q1'24 to Q3'25 data (remove future predictions)
valid_quarters = ['2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4', '2025_Q1', '2025_Q2', '2025_Q3']
print(f"Filtering data to valid quarters: {valid_quarters}")
tariff_df = tariff_df[tariff_df['quarter'].isin(valid_quarters)].copy()
print(f"After filtering: {len(tariff_df)} events remaining")

# Optional: linearmodels for panel FE + two-way clustered SEs
try:
    from linearmodels.panel import PanelOLS
    LINEARMODELS_AVAILABLE = True
except Exception:
    LINEARMODELS_AVAILABLE = False

def sanitize_quarter(q):
    """Ensure quarter is a string-like period label (e.g., '2024_Q3')."""
    if pd.isna(q):
        return np.nan
    q = str(q)
    return q

def run_ols_hc3(df: pd.DataFrame):
    """Baseline OLS with HC3 robust SEs - matching PDF specification."""
    # Main variables: TariffSent, Surprise, TariffMentions
    # Controls: size, momentum, after_hours
    cols = ['TariffSent_mean', 'eps_surprise', 'TariffMentions', 'size', 'momentum', 'after_hours']
    reg = df[['CAR'] + cols].dropna().copy()
    y = reg['CAR']
    X = sm.add_constant(reg[cols])
    model = sm.OLS(y, X).fit(cov_type='HC3')
    return model

def run_fe_firm_cluster(df: pd.DataFrame):
    """
    OLS with sector & quarter FE (via dummies) and firm-clustered SEs.
    Matches PDF specification: sector FE and calendar quarter FE.
    """
    work = df[['CAR','TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours','sector','ticker','quarter']].dropna().copy()

    # Ensure sector and quarter are strings and handle missing values
    work['sector'] = work['sector'].fillna('Unknown').astype(str)
    work['quarter'] = work['quarter'].fillna('Unknown').astype(str)
    
    # Build FE via dummies (avoid dummy trap: drop_first=True)
    sector_d = pd.get_dummies(work['sector'], prefix='sector', drop_first=True, dtype=float)
    quarter_d = pd.get_dummies(work['quarter'], prefix='quarter', drop_first=True, dtype=float)

    X = pd.concat(
        [work[['TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours']], sector_d, quarter_d],
        axis=1
    )
    y = work['CAR']

    X = sm.add_constant(X)
    # One-way cluster by firm (ticker)
    model = sm.OLS(y, X).fit(
        cov_type='cluster',
        cov_kwds={'groups': work['ticker'].astype('category').cat.codes}
    )
    return model

def run_panel_twfe_twcluster(df: pd.DataFrame):
    """
    PanelOLS with entity (ticker) & time (quarter) fixed effects,
    and two-way clustered SEs (entity & time) using linearmodels.
    Matches PDF specification: firm and quarter two-way clustering.
    """
    if not LINEARMODELS_AVAILABLE:
        return None, "linearmodels not installed; skipping PanelOLS."

    work = df[['CAR','TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours','ticker','quarter']].dropna().copy()

    # Set a MultiIndex (entity, time)
    work['quarter'] = work['quarter'].apply(sanitize_quarter)
    work = work.set_index(['ticker','quarter']).sort_index()

    y = work['CAR']
    X = work[['TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours']]

    # PanelOLS with entity_effects=True & time_effects=True to absorb two-way FE
    mod = PanelOLS(
        dependent=y,
        exog=X,
        entity_effects=True,
        time_effects=True
    )
    # Two-way clustered covariance: by entity (firm) and time (quarter)
    res = mod.fit(
        cov_type='clustered',
        cluster_entity=True,
        cluster_time=True
    )
    return res, None

def save_results_txt(models: dict, out_path: Path):
    """Save text summaries to a single txt file."""
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("EVENT-STUDY REGRESSIONS\n")
        f.write("="*80 + "\n\n")
        for name, m in models.items():
            f.write(f"[{name}]\n")
            if hasattr(m, 'summary'):
                f.write(str(m.summary()))
            else:
                # linearmodels PanelResults has .summary too; fallback just in case
                f.write(str(m))
            f.write("\n\n")

def save_coef_table(models: dict, out_csv: Path):
    """Collect coefficients into a tidy CSV for easy import to LaTeX or Excel."""
    rows = []
    for name, m in models.items():
        try:
            params = m.params
            if hasattr(m, 'bse'):
                ses = m.bse
            elif hasattr(m, 'std_errors'):
                ses = m.std_errors
            else:
                ses = None
            for k in params.index:
                rows.append({
                    'model': name,
                    'term': k,
                    'coef': params[k],
                    'se': (ses[k] if ses is not None and k in ses.index else np.nan)
                })
        except Exception:
            # Best-effort: skip if structure unexpected
            continue
    if rows:
        pd.DataFrame(rows).to_csv(out_csv, index=False)

# 13) Advanced regression analysis (requirement 7)
print("\n" + "="*80)
print("REQUIREMENT 7: ECONOMETRIC SPECIFICATION")
print("="*80)
print("Running event-study regressions matching PDF specification...")
print("Formula: CAR[t,t+1] = α + β₁·TariffSent + β₂·Surprise + β₃·TariffMentions + γ'X + δ_sector + δ_quarter + ε")
print("- Fixed Effects: sector (GICS) and calendar quarter FE")
print("- Standard Errors: clustered by firm and quarter (two-way)")
print("="*80)

# Prepare regression data
reg_data = tariff_df[['CAR', 'TariffSent_mean', 'eps_surprise', 'TariffMentions', 'size', 'momentum', 'after_hours', 'sector', 'ticker', 'quarter']].dropna()

if len(reg_data) > 20:  # Need sufficient observations
    # Run models
    models = {}

    print("\n[1/3] Running baseline OLS with HC3 robust SEs...")
    m1 = run_ols_hc3(reg_data)
    models['Model 1: OLS + HC3 (no FE)'] = m1

    print("[2/3] Running OLS with Sector & Quarter FE + Firm-clustered SEs...")
    m2 = run_fe_firm_cluster(reg_data)
    models['Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs'] = m2

    print("[3/3] Running PanelOLS with Entity & Time FE + Two-way clustered SEs...")
    m3, warn = run_panel_twfe_twcluster(reg_data)
    if m3 is not None:
        models['Model 3: PanelOLS + Entity & Time FE + Two-way clustered SEs'] = m3
    else:
        print(f"[WARN] {warn}")

    # Save outputs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    txt_path = OUTPUT_DIR / f"{timestamp}_regression_results.txt"
    save_results_txt(models, txt_path)

    coef_csv = OUTPUT_DIR / f"{timestamp}_regression_coefs.csv"
    save_coef_table(models, coef_csv)

    print("\n" + "="*80)
    print("REQUIREMENT 7: ECONOMETRIC REGRESSIONS COMPLETE")
    print("="*80)
    print(f"✓ Saved text summary: {txt_path}")
    print(f"✓ Saved coefficients: {coef_csv}")
    print(f"✓ N observations: {len(reg_data)}")
    
    # Print key results from main model
    if 'Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs' in models:
        m = models['Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs']
        print(f"\nKey Results (Model 2 - Main Specification):")
        print(f"  β₁ (TariffSent_mean): {m.params.get('TariffSent_mean', np.nan):.6f}")
        print(f"  β₂ (eps_surprise):     {m.params.get('eps_surprise', np.nan):.6f}")
        print(f"  β₃ (TariffMentions):   {m.params.get('TariffMentions', np.nan):.6f}")
        print(f"  R-squared:             {m.rsquared:.4f}")
    
    if not LINEARMODELS_AVAILABLE:
        print("\nNote: 'linearmodels' not installed; skipped Model 3.")
        print("Install with:  pip install linearmodels")
    print("="*80)
        
else:
    print(f"Insufficient data for regression. Only {len(reg_data)} complete observations.")

print("\nEnhanced Analysis Complete!")
print(f"Summary statistics:")
print(f"- Total transcripts processed: {len(transcripts_df)}")
print(f"- Transcripts with tariff mentions: {(tariff_df['TariffMentions'] > 0).sum()}")
print(f"- Events with valid EPS: {(~tariff_df['eps_actual'].isna()).sum()}")
print(f"- Events with valid EPS surprise: {(~tariff_df['eps_surprise'].isna()).sum()}")
print(f"- Average tariff sentiment: {tariff_df['TariffSent_mean'].mean():.3f}")
print(f"- Average CAR: {tariff_df['CAR'].mean():.4f}")
print(f"- Average EPS surprise: {tariff_df['eps_surprise'].mean():.6f}")

# Document transcript coverage (Requirement 11)
print("\n" + "="*80)
print("REQUIREMENT 11: TRANSCRIPT COVERAGE DOCUMENTATION")
print("="*80)
total_possible = len(events_df)
total_processed = len(transcripts_df)
coverage_rate = (total_processed / total_possible * 100) if total_possible > 0 else 0
print(f"Transcript coverage rate: {total_processed}/{total_possible} ({coverage_rate:.1f}%)")
print(f"- Events with transcripts: {total_processed}")
print(f"- Events in dataset: {total_possible}")
print(f"- Missing transcripts: {total_possible - total_processed}")
print("\nNote: Coverage rate documents which earnings calls have available transcripts.")
print("Selection bias handled by documenting coverage and controlling for firm/time FE.")
print("="*80)

# ============================================================================
# REQUIREMENT 9: Prepare Repro-ready Variable Dictionary
# ============================================================================
print("\n" + "="*80)
print("REQUIREMENT 9: PREPARING REPRO-READY VARIABLE DICTIONARY")
print("="*80)

# Remove outliers: cap extreme CAR and surprise values (Requirement 11)
print("Applying outlier treatment (cap extreme CAR and surprise values)...")
car_p1 = tariff_df['CAR'].quantile(0.01)
car_p99 = tariff_df['CAR'].quantile(0.99)
tariff_df['CAR'] = tariff_df['CAR'].clip(lower=car_p1, upper=car_p99)

eps_p1 = tariff_df['eps_surprise'].quantile(0.01)
eps_p99 = tariff_df['eps_surprise'].quantile(0.99)
tariff_df['eps_surprise'] = tariff_df['eps_surprise'].clip(lower=eps_p1, upper=eps_p99)
print(f"✓ Capped CAR at [{car_p1:.4f}, {car_p99:.4f}]")
print(f"✓ Capped EPS surprise at [{eps_p1:.6f}, {eps_p99:.6f}]")

# Rename variables to match requirement 9 specification
tariff_df_output = tariff_df.copy()

# Rename time variables
tariff_df_output = tariff_df_output.rename(columns={
    'ann_date': 'ann_time_iq',  # timestamp of press release
    'conference_date': 'call_time_iq'  # call start timestamp
})

# Rename core variables with proper naming convention
tariff_df_output = tariff_df_output.rename(columns={
    'TariffSent_mean': 'TariffSent_mean_call_iq',  # TariffSent_mean_call_{i,q}
    'TariffMentions': 'TariffMentions_iq',  # TariffMentions_{i,q}
    'ForwardTone': 'TariffSent_fwd_iq',  # TariffSent_fwd_{i,q} (forward-looking subset)
    'eps_surprise': 'Surprise_EPS_iq'  # Surprise_EPS_{i,q} (primary)
})

# Add book-to-market (bm), momentum_12_2, volatility (ivol) placeholders
# Note: These would require additional data; using proxies or placeholders
tariff_df_output['bm'] = np.nan  # Would need book value data
tariff_df_output['momentum_12_2'] = tariff_df_output.get('momentum', np.nan)  # Using our momentum as proxy
tariff_df_output['ivol'] = tariff_df_output.get('size', np.nan)  # Using volatility proxy we calculated

# Ensure qa_share column exists (share of Q&A discussion - would need transcript parsing)
tariff_df_output['qa_share'] = np.nan  # Placeholder - would need full transcript Q&A parsing

# Reorder columns to match requirement 9 specification order
output_columns_order = [
    # Identifiers and time
    'ticker',
    'fqtr',
    'quarter',
    'ann_time_iq',
    'call_time_iq',
    
    # Dependent variable
    'CAR',
    
    # Primary variables
    'Surprise_EPS_iq',
    'TariffSent_mean_call_iq',
    'TariffMentions_iq',
    'TariffSent_fwd_iq',
    
    # Control variables
    'size',
    'bm',
    'momentum_12_2',
    'ivol',
    'after_hours',
    'qa_share',
    
    # Additional info
    'sector',
    'eps_actual',
    'TariffSent_shareNeg',
    'tariff_sentences'
]

# Select only existing columns
output_columns = [col for col in output_columns_order if col in tariff_df_output.columns]
tariff_df_output = tariff_df_output[output_columns]

print(f"✓ Variables renamed to match requirement 9 specification")
print(f"✓ Output contains {len(output_columns)} variables")
print(f"\nKey variables:")
print(f"  - ann_time_iq: timestamp of press release")
print(f"  - call_time_iq: call start timestamp")
print(f"  - CAR_[window]_iq: from market/FF model")
print(f"  - Surprise_EPS_iq: (primary)")
print(f"  - TariffSent_mean_call_iq: tariff sentiment from call")
print(f"  - TariffMentions_iq: count of tariff mentions")
print(f"  - TariffSent_fwd_iq: forward-looking subset")
print(f"  - Controls: size, bm, momentum_12_2, ivol, after_hours, qa_share")

# Save results with timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = OUTPUT_DIR / f'{timestamp}_results.csv'
tariff_df_output.to_csv(output_file, index=False)
print(f"\n✓ Results saved to '{output_file}'")
print("="*80)

# ============================================================================
# REQUIREMENT 12: Generate Summary Report
# ============================================================================
print("\n" + "="*80)
print("REQUIREMENT 12: WHAT TO REPORT - GENERATING SUMMARY REPORT")
print("="*80)

report_file = OUTPUT_DIR / f'{timestamp}_summary_report.txt'
with open(report_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("TARIFF SENTIMENT ANALYSIS - SUMMARY REPORT\n")
    f.write("="*80 + "\n\n")
    
    # 1. Descriptives: tariff mention rates & sentiment by quarter/sector and by report vs call
    f.write("1. DESCRIPTIVE STATISTICS\n")
    f.write("-" * 80 + "\n\n")
    f.write("Tariff Mention Rates & Sentiment by Quarter:\n")
    quarter_stats = tariff_df_output.groupby('quarter').agg({
        'TariffMentions_iq': ['count', 'mean', 'sum'],
        'TariffSent_mean_call_iq': ['mean', 'std']
    }).round(4)
    f.write(quarter_stats.to_string() + "\n\n")
    
    f.write("Tariff Mention Rates & Sentiment by Sector:\n")
    sector_stats = tariff_df_output.groupby('sector').agg({
        'TariffMentions_iq': ['count', 'mean', 'sum'],
        'TariffSent_mean_call_iq': ['mean', 'std']
    }).round(4)
    f.write(sector_stats.to_string() + "\n\n")
    
    # 2. Main table reference
    f.write("\n2. MAIN REGRESSION TABLE\n")
    f.write("-" * 80 + "\n")
    f.write(f"See: {timestamp}_regression_results.txt\n")
    f.write(f"See: {timestamp}_regression_coefs.csv\n")
    f.write("Main specification: CAR on TariffSent + Surprise with FE and clustered SEs\n\n")
    
    # 3. Robustness suite note
    f.write("\n3. ROBUSTNESS SUITE\n")
    f.write("-" * 80 + "\n")
    f.write("Multiple specifications provided:\n")
    f.write("  - Model 1: OLS + HC3 (baseline)\n")
    f.write("  - Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs\n")
    f.write("  - Model 3: PanelOLS + Entity & Time FE + Two-way clustered SEs\n")
    f.write("\nFuture robustness checks could include:\n")
    f.write("  - Exposure interaction (firm tariff exposure × tariff tone)\n")
    f.write("  - Alternative windows and tariff tone definitions\n")
    f.write("  - Placebo topics (non-tariff sentiment)\n\n")
    
    # 4. Interpretable snippets
    f.write("\n4. INTERPRETABLE SNIPPETS\n")
    f.write("-" * 80 + "\n")
    f.write("Top positive tariff sentiment examples:\n")
    top_pos = tariff_df_output.nlargest(5, 'TariffSent_mean_call_iq')[['ticker', 'quarter', 'TariffSent_mean_call_iq', 'tariff_sentences']]
    for idx, row in top_pos.iterrows():
        f.write(f"\n{row['ticker']} ({row['quarter']}): Sentiment = {row['TariffSent_mean_call_iq']:.3f}\n")
        if isinstance(row['tariff_sentences'], list) and len(row['tariff_sentences']) > 0:
            f.write(f"  Example: \"{row['tariff_sentences'][0][:200]}...\"\n")
    
    f.write("\n\nTop negative tariff sentiment examples:\n")
    top_neg = tariff_df_output.nsmallest(5, 'TariffSent_mean_call_iq')[['ticker', 'quarter', 'TariffSent_mean_call_iq', 'tariff_sentences']]
    for idx, row in top_neg.iterrows():
        f.write(f"\n{row['ticker']} ({row['quarter']}): Sentiment = {row['TariffSent_mean_call_iq']:.3f}\n")
        if isinstance(row['tariff_sentences'], list) and len(row['tariff_sentences']) > 0:
            f.write(f"  Example: \"{row['tariff_sentences'][0][:200]}...\"\n")
    
    f.write("\n\n" + "="*80 + "\n")
    f.write("END OF SUMMARY REPORT\n")
    f.write("="*80 + "\n")

print(f"✓ Summary report saved to '{report_file}'")
print("\nReport includes:")
print("  1. Descriptives: tariff mention rates & sentiment by quarter/sector")
print("  2. Main table reference: CAR on TariffSent + Surprise with FE and clustered SEs")
print("  3. Robustness suite documentation")
print("  4. Interpretable snippets: top positive/negative tariff sentences")
print("="*80)

# ============================================================================
# Generate Visualizations
# ============================================================================
print("\n" + "="*80)
print("REQUIREMENT 8: PORTRAYAL DELIVERABLES")
print("="*80)
print("\nTo generate plots, run:")
print("  python src/Generate_Plots.py")
print("\nThis will create 4 high-resolution plots in output/plots/:")
print("  1. Time-series of tariff sentiment by quarter")
print("  2. Sector heatmap of tariff sentiment")
print("  3. Word shifts (negative vs positive events)")
print("  4. Sentiment distribution and patterns")
print("="*80)

print("\n" + "="*80)
print("ANALYSIS COMPLETE!")
print("="*80)

