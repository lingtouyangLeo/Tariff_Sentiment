"""
Regression Analysis - Requirement 7 and beyond
Loads processed data from output folder and runs all regression analyses
Usage: python src/Regressions.py
"""

import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
import pandas as pd
import numpy as np
import statsmodels.api as sm
from datetime import datetime
from pathlib import Path
import sys
import glob

# Set up directory paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'dataset'
OUTPUT_DIR = BASE_DIR / 'output'

print("="*80)
print("REGRESSION ANALYSIS - LOADING PROCESSED DATA")
print("="*80)

# Load most recent processed data
pkl_files = sorted(glob.glob(str(OUTPUT_DIR / '*_tariff_data.pkl')), reverse=True)
if not pkl_files:
    print("ERROR: No processed data files found!")
    print("Please run Tariff_Sentiment.py first to generate processed data.")
    sys.exit(1)

tariff_data_file = Path(pkl_files[0])
print(f"✓ Loading processed data from: {tariff_data_file.name}")
tariff_df = pd.read_pickle(tariff_data_file)
print(f"✓ Loaded {len(tariff_df)} events")
print(f"✓ Date range: {tariff_df['ann_date'].min()} to {tariff_df['ann_date'].max()}")

# Check for linearmodels
try:
    from linearmodels.panel import PanelOLS
    LINEARMODELS_AVAILABLE = True
except Exception:
    LINEARMODELS_AVAILABLE = False
    print("⚠️  Warning: linearmodels not available, Model 3 will be skipped")

# Define regression functions
def sanitize_quarter(q):
    """Ensure quarter is a string-like period label (e.g., '2024_Q3')."""
    if pd.isna(q):
        return np.nan
    q = str(q)
    return q

def run_ols_hc3(df: pd.DataFrame):
    """Baseline OLS with HC3 robust SEs - matching PDF specification."""
    cols = ['TariffSent_mean', 'eps_surprise', 'TariffMentions', 'size', 'momentum', 'after_hours']
    reg = df[['CAR'] + cols].dropna().copy()
    y = reg['CAR']
    X = sm.add_constant(reg[cols])
    model = sm.OLS(y, X).fit(cov_type='HC3')
    return model

def run_fe_firm_cluster(df: pd.DataFrame):
    """OLS with sector & quarter FE (via dummies) and firm-clustered SEs."""
    work = df[['CAR','TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours','sector','ticker','quarter']].dropna().copy()
    work['sector'] = work['sector'].fillna('Unknown').astype(str)
    work['quarter'] = work['quarter'].fillna('Unknown').astype(str)
    
    sector_d = pd.get_dummies(work['sector'], prefix='sector', drop_first=True, dtype=float)
    quarter_d = pd.get_dummies(work['quarter'], prefix='quarter', drop_first=True, dtype=float)
    
    X = pd.concat(
        [work[['TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours']], sector_d, quarter_d],
        axis=1
    )
    y = work['CAR']
    X = sm.add_constant(X)
    
    model = sm.OLS(y, X).fit(
        cov_type='cluster',
        cov_kwds={'groups': work['ticker'].astype('category').cat.codes}
    )
    return model

def run_panel_twfe_twcluster(df: pd.DataFrame):
    """PanelOLS with entity & time FE + two-way clustered SEs."""
    if not LINEARMODELS_AVAILABLE:
        return None, "linearmodels not installed; skipping PanelOLS."
    
    work = df[['CAR','TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours','ticker','quarter']].dropna().copy()
    
    # Convert quarter to numeric for PanelOLS
    def quarter_to_numeric(q):
        if pd.isna(q):
            return np.nan
        q = str(q)
        parts = q.split('_Q')
        if len(parts) == 2:
            return int(parts[0]) * 10 + int(parts[1])
        return np.nan
    
    work['quarter_numeric'] = work['quarter'].apply(quarter_to_numeric)
    work = work.set_index(['ticker','quarter_numeric']).sort_index()
    
    y = work['CAR']
    X = work[['TariffSent_mean','eps_surprise','TariffMentions','size','momentum','after_hours']]
    
    mod = PanelOLS(
        dependent=y,
        exog=X,
        entity_effects=True,
        time_effects=True
    )
    
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
                # Check if summary is a method or property
                summary = m.summary() if callable(m.summary) else m.summary
                f.write(str(summary))
            else:
                f.write(str(m))
            f.write("\n\n")

def save_coef_table(models: dict, out_csv: Path):
    """Collect coefficients into a tidy CSV."""
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
            continue
    if rows:
        pd.DataFrame(rows).to_csv(out_csv, index=False)

# Run regressions
print("\n" + "="*80)
print("REQUIREMENT 7: ECONOMETRIC SPECIFICATION")
print("="*80)
print("Formula: CAR[t,t+1] = α + β₁·TariffSent + β₂·Surprise + β₃·TariffMentions + γ'X + δ_sector + δ_quarter + ε")
print("="*80)

reg_data = tariff_df[['CAR', 'TariffSent_mean', 'eps_surprise', 'TariffMentions', 'size', 'momentum', 'after_hours', 'sector', 'ticker', 'quarter']].dropna()

if len(reg_data) > 20:
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
    print("REGRESSIONS COMPLETE")
    print("="*80)
    print(f"✓ Saved text summary: {txt_path}")
    print(f"✓ Saved coefficients: {coef_csv}")
    print(f"✓ N observations: {len(reg_data)}")
    
    # Print key results
    if 'Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs' in models:
        m = models['Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs']
        print(f"\nKey Results (Model 2 - Main Specification):")
        print(f"  β₁ (TariffSent_mean): {m.params.get('TariffSent_mean', np.nan):.6f}")
        print(f"  β₂ (eps_surprise):     {m.params.get('eps_surprise', np.nan):.6f}")
        print(f"  β₃ (TariffMentions):   {m.params.get('TariffMentions', np.nan):.6f}")
        print(f"  R-squared:             {m.rsquared:.4f}")
    
    print("="*80)
else:
    print(f"ERROR: Insufficient data for regression. Only {len(reg_data)} complete observations.")

print("\n✓ Regression analysis complete!")
print(f"✓ Results saved to: {OUTPUT_DIR}")

# ============================================================================
# REQUIREMENT 9: VARIABLE NAME MAPPING (for final output CSV)
# ============================================================================

print("\n" + "="*80)
print("REQUIREMENT 9: VARIABLE NAME MAPPING")
print("="*80)

VAR_DICT = {
    'TariffMentions': 'TariffMentions_iq',
    'TariffSent_mean': 'TariffSent_mean_call_iq',
    'size': 'Size_iq',
    'momentum': 'Momentum_iq',
    'after_hours': 'AfterHours_iq',
    'sector': 'Sector_i',
    'quarter': 'Quarter_q',
    'CAR': 'CAR_iq',
    'eps_surprise': 'Surprise_iq',
    'ticker': 'Ticker_i'
}

print("Variable name mapping:")
for old, new in VAR_DICT.items():
    print(f"  {old:20s} → {new}")

# ============================================================================
# REQUIREMENT 11: OUTLIER TREATMENT (winsorization at 1%/99%)
# ============================================================================

print("\n" + "="*80)
print("REQUIREMENT 11: OUTLIER TREATMENT")
print("="*80)

def winsorize(series, lower=0.01, upper=0.99):
    """Winsorize a series at the given percentiles."""
    if series.isna().all():
        return series
    q_low = series.quantile(lower)
    q_high = series.quantile(upper)
    return series.clip(lower=q_low, upper=q_high)

tariff_final = tariff_df.copy()

# Apply winsorization to continuous variables
winsorize_vars = ['CAR', 'TariffSent_mean', 'eps_surprise', 'TariffMentions', 'size', 'momentum']
print(f"\nApplying winsorization (1%/99%) to: {', '.join(winsorize_vars)}")

for var in winsorize_vars:
    if var in tariff_final.columns:
        before_min = tariff_final[var].min()
        before_max = tariff_final[var].max()
        tariff_final[var] = winsorize(tariff_final[var])
        after_min = tariff_final[var].min()
        after_max = tariff_final[var].max()
        print(f"  {var:20s}: [{before_min:10.4f}, {before_max:10.4f}] → [{after_min:10.4f}, {after_max:10.4f}]")

# Rename variables according to REQUIREMENT 9
print("\nRenaming variables for final output...")
tariff_final.rename(columns=VAR_DICT, inplace=True)

# Save final CSV with renamed variables and winsorized data
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
final_csv = OUTPUT_DIR / f"{timestamp}_results.csv"
tariff_final.to_csv(final_csv, index=False)
print(f"\n✓ Final results saved to: {final_csv}")
print(f"✓ Total events: {len(tariff_final)}")

# ============================================================================
# REQUIREMENT 12: SUMMARY REPORT
# ============================================================================

print("\n" + "="*80)
print("REQUIREMENT 12: SUMMARY REPORT")
print("="*80)

summary_file = OUTPUT_DIR / f"{timestamp}_summary_report.txt"

with open(summary_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("TARIFF SENTIMENT ANALYSIS - SUMMARY REPORT\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("="*80 + "\n\n")
    
    # Dataset overview
    f.write("1. DATASET OVERVIEW\n")
    f.write("-" * 80 + "\n")
    f.write(f"Total observations: {len(tariff_final)}\n")
    f.write(f"Date range: {tariff_df['ann_date'].min()} to {tariff_df['ann_date'].max()}\n")
    f.write(f"Unique companies: {tariff_df['ticker'].nunique()}\n")
    f.write(f"Unique quarters: {tariff_df['quarter'].nunique()}\n")
    f.write(f"Unique sectors: {tariff_df['sector'].nunique()}\n\n")
    
    # Descriptive statistics
    f.write("2. DESCRIPTIVE STATISTICS (after winsorization)\n")
    f.write("-" * 80 + "\n")
    desc_cols = ['CAR_iq', 'TariffSent_mean_call_iq', 'Surprise_iq', 'TariffMentions_iq', 'Size_iq', 'Momentum_iq']
    desc_cols = [c for c in desc_cols if c in tariff_final.columns]
    if desc_cols:
        desc_stats = tariff_final[desc_cols].describe()
        f.write(desc_stats.to_string() + "\n\n")
    
    # Sample of data
    f.write("3. SAMPLE DATA (first 10 rows)\n")
    f.write("-" * 80 + "\n")
    sample_cols = ['Ticker_i', 'Quarter_q', 'CAR_iq', 'TariffSent_mean_call_iq', 'TariffMentions_iq']
    sample_cols = [c for c in sample_cols if c in tariff_final.columns]
    if sample_cols:
        f.write(tariff_final[sample_cols].head(10).to_string(index=False) + "\n\n")
    
    # Regression results summary
    f.write("4. REGRESSION RESULTS SUMMARY\n")
    f.write("-" * 80 + "\n")
    f.write("Three econometric specifications were estimated:\n\n")
    
    f.write("Model 1: Baseline OLS with HC3 robust standard errors\n")
    f.write("  - No fixed effects\n")
    f.write("  - Heteroskedasticity-robust standard errors (HC3)\n\n")
    
    f.write("Model 2: OLS with Sector & Quarter Fixed Effects (PREFERRED SPECIFICATION)\n")
    f.write("  - Sector fixed effects (controls for industry-specific factors)\n")
    f.write("  - Quarter fixed effects (controls for time-varying aggregate shocks)\n")
    f.write("  - Firm-clustered standard errors (accounts for within-firm correlation)\n\n")
    
    f.write("Model 3: PanelOLS with Two-Way Fixed Effects\n")
    f.write("  - Entity (firm) fixed effects\n")
    f.write("  - Time (quarter) fixed effects\n")
    f.write("  - Two-way clustered standard errors (entity + time)\n\n")
    
    if 'Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs' in models:
        m2 = models['Model 2: OLS + Sector & Quarter FE + Firm-clustered SEs']
        f.write("Key Findings (Model 2):\n")
        f.write(f"  • TariffSent_mean coefficient: {m2.params.get('TariffSent_mean', np.nan):.6f}\n")
        f.write(f"  • eps_surprise coefficient:     {m2.params.get('eps_surprise', np.nan):.6f}\n")
        f.write(f"  • TariffMentions coefficient:   {m2.params.get('TariffMentions', np.nan):.6f}\n")
        f.write(f"  • R-squared:                    {m2.rsquared:.4f}\n")
        f.write(f"  • Observations:                 {int(m2.nobs)}\n\n")
    
    # Data quality notes
    f.write("5. DATA QUALITY & ROBUSTNESS\n")
    f.write("-" * 80 + "\n")
    f.write("Outlier Treatment:\n")
    f.write("  - Winsorization applied at 1st and 99th percentiles\n")
    f.write(f"  - Variables treated: {', '.join(winsorize_vars)}\n\n")
    
    f.write("Missing Data:\n")
    missing_pct = (tariff_df[['CAR', 'TariffSent_mean', 'eps_surprise']].isna().sum() / len(tariff_df) * 100)
    for var, pct in missing_pct.items():
        f.write(f"  - {var}: {pct:.2f}% missing\n")
    f.write("\n")
    
    f.write("Control Variables:\n")
    f.write("  - Size: Log market capitalization\n")
    f.write("  - Momentum: Prior 6-month returns\n")
    f.write("  - AfterHours: Indicator for announcements outside trading hours\n")
    f.write("  - Sector: GICS industry classification\n")
    f.write("  - Quarter: Fiscal quarter fixed effects\n\n")
    
    # Interpretation
    f.write("6. INTERPRETATION\n")
    f.write("-" * 80 + "\n")
    f.write("This analysis examines the relationship between tariff-related sentiment in\n")
    f.write("earnings calls and stock returns. The dependent variable is the 2-day cumulative\n")
    f.write("abnormal return (CAR) around the earnings announcement.\n\n")
    
    f.write("Key Variables:\n")
    f.write("  - TariffSent_mean_call_iq: Average FinBERT sentiment of tariff-related sentences\n")
    f.write("  - TariffMentions_iq: Number of tariff mentions in the call\n")
    f.write("  - Surprise_iq: Earnings surprise (actual - consensus) / price\n\n")
    
    f.write("Expected Relationships:\n")
    f.write("  - Positive sentiment → Positive CAR (β₁ > 0)\n")
    f.write("  - Positive surprise → Positive CAR (β₂ > 0)\n")
    f.write("  - More mentions → Greater market attention (β₃ effect ambiguous)\n\n")
    
    # Files generated
    f.write("7. OUTPUT FILES GENERATED\n")
    f.write("-" * 80 + "\n")
    f.write(f"  - {final_csv.name} (final data with renamed variables)\n")
    f.write(f"  - {txt_path.name} (regression output)\n")
    f.write(f"  - {coef_csv.name} (coefficient table)\n")
    f.write(f"  - {summary_file.name} (this report)\n\n")
    
    f.write("="*80 + "\n")
    f.write("END OF REPORT\n")
    f.write("="*80 + "\n")

print(f"\n✓ Summary report saved to: {summary_file}")

# ============================================================================
# FINAL COMPLETION MESSAGE
# ============================================================================

print("\n" + "="*80)
print("✅ ALL REQUIREMENTS COMPLETE")
print("="*80)
print(f"\n📊 Generated outputs in: {OUTPUT_DIR}")
print(f"\n1. Regression results:")
print(f"   - {txt_path.name}")
print(f"   - {coef_csv.name}")
print(f"\n2. Final data:")
print(f"   - {final_csv.name}")
print(f"\n3. Summary report:")
print(f"   - {summary_file.name}")
print(f"\n4. Visualizations (run Generate_Plots.py):")
print(f"   - Time series sentiment plot")
print(f"   - Sector heatmap")
print(f"   - Word frequency shifts")
print(f"   - Sentiment distribution analysis")
print("\n" + "="*80)
print("✅ Regression analysis pipeline complete!")
print("="*80)
