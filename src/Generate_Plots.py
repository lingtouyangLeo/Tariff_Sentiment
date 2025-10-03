"""
Generate Requirement 8 Plots from CSV Results
This script creates all Requirement 8 visualizations from the saved results file.
Run this after Tariff_Sentiment.py completes.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import os
import ast
import re
from pathlib import Path

# Set up directory paths
BASE_DIR = Path(__file__).parent.parent  # Project root directory
OUTPUT_DIR = BASE_DIR / 'output'
PLOTS_DIR = OUTPUT_DIR / 'plots'

print("="*80)
print("REQUIREMENT 8: GENERATING VISUALIZATIONS FROM CSV")
print("="*80)

# Find the most recent results file (by modification time)
results_files = list(OUTPUT_DIR.glob('*_results.csv'))
if not results_files:
    print(f"\n❌ ERROR: No results file found in {OUTPUT_DIR}!")
    print("Please run Tariff_Sentiment.py first to generate the results.")
    print("Looking for files matching pattern: *_results.csv")
    exit(1)

# Sort by modification time (most recent first)
results_files = sorted(results_files, key=lambda x: x.stat().st_mtime, reverse=True)
results_file = results_files[0]  # Get the most recent file
print(f"\n✓ Found {len(results_files)} results file(s)")
print(f"✓ Loading most recent: {results_file.name}...")
tariff_df = pd.read_csv(results_file)

# Parse tariff_sentences from string representation back to list
print("✓ Parsing tariff sentences...")
def safe_parse_list(x):
    if pd.isna(x) or x == '[]' or x == '':
        return []
    try:
        return ast.literal_eval(x)
    except:
        return []

tariff_df['tariff_sentences'] = tariff_df['tariff_sentences'].apply(safe_parse_list)

# Create output directory for plots
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

print(f"\nData Summary:")
print(f"- Total events: {len(tariff_df)}")
print(f"- Events with tariff mentions: {(tariff_df['TariffMentions'] > 0).sum()}")
print(f"- Date range: {tariff_df['conference_date'].min()} to {tariff_df['conference_date'].max()}")

# Filter to only include Q1'24 to Q3'25 data (remove future predictions)
valid_quarters = ['2024_Q1', '2024_Q2', '2024_Q3', '2024_Q4', '2025_Q1', '2025_Q2', '2025_Q3']
tariff_df = tariff_df[tariff_df['quarter'].isin(valid_quarters)].copy()
print(f"- After quarter filtering: {len(tariff_df)} events")

# Filter to events with tariff mentions
tariff_df_with_tariffs = tariff_df[tariff_df['TariffMentions'] > 0].copy()
print(f"- Analyzing {len(tariff_df_with_tariffs)} events with tariff content")

# Use the existing 'quarter' column (already formatted as 'YYYY_QX')
# Rename for consistency with the rest of the code
tariff_df_with_tariffs['year_quarter'] = tariff_df_with_tariffs['quarter']

# ============================================================================
# 8.1) Time-series of average tariff sentiment by quarter
# ============================================================================
print("\n" + "="*80)
print("8.1) TIME-SERIES ANALYSIS")
print("="*80)

# Calculate quarterly averages
quarterly_sentiment = tariff_df_with_tariffs.groupby('year_quarter').agg({
    'TariffSent_mean': ['mean', 'std', 'count'],
    'TariffMentions': 'mean',
    'TariffSent_shareNeg': 'mean'
}).round(4)

quarterly_sentiment.columns = ['Sentiment_Mean', 'Sentiment_Std', 'N_Events', 'Avg_Mentions', 'Share_Negative']
quarterly_sentiment = quarterly_sentiment.sort_index()

print("\nQuarterly Statistics:")
print(quarterly_sentiment.to_string())

# Create time series plot
fig, axes = plt.subplots(2, 2, figsize=(16, 10))

# Plot 1: Sentiment over time
axes[0, 0].plot(quarterly_sentiment.index, quarterly_sentiment['Sentiment_Mean'], 
                marker='o', linewidth=2.5, markersize=10, color='#2E86AB', label='Average Sentiment')
axes[0, 0].axhline(y=0, color='red', linestyle='--', alpha=0.6, linewidth=2, label='Neutral')
axes[0, 0].fill_between(range(len(quarterly_sentiment)), 
                        quarterly_sentiment['Sentiment_Mean'] - quarterly_sentiment['Sentiment_Std'],
                        quarterly_sentiment['Sentiment_Mean'] + quarterly_sentiment['Sentiment_Std'],
                        alpha=0.2, color='#2E86AB')
axes[0, 0].set_xlabel('Quarter', fontsize=12, fontweight='bold')
axes[0, 0].set_ylabel('Average Tariff Sentiment', fontsize=12, fontweight='bold')
axes[0, 0].set_title('Tariff Sentiment Evolution Over Time', fontsize=14, fontweight='bold')
axes[0, 0].set_xticks(range(len(quarterly_sentiment)))
axes[0, 0].set_xticklabels(quarterly_sentiment.index, rotation=45, ha='right')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].legend(fontsize=10)

# Plot 2: Mentions over time
axes[0, 1].plot(quarterly_sentiment.index, quarterly_sentiment['Avg_Mentions'], 
                marker='s', linewidth=2.5, markersize=10, color='#A23B72', label='Average Mentions')
axes[0, 1].set_xlabel('Quarter', fontsize=12, fontweight='bold')
axes[0, 1].set_ylabel('Average Tariff Mentions per Event', fontsize=12, fontweight='bold')
axes[0, 1].set_title('Tariff Mention Frequency Over Time', fontsize=14, fontweight='bold')
axes[0, 1].set_xticks(range(len(quarterly_sentiment)))
axes[0, 1].set_xticklabels(quarterly_sentiment.index, rotation=45, ha='right')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].legend(fontsize=10)

# Plot 3: Number of events
axes[1, 0].bar(range(len(quarterly_sentiment)), quarterly_sentiment['N_Events'], 
               color='#F18F01', edgecolor='black', alpha=0.7)
axes[1, 0].set_xlabel('Quarter', fontsize=12, fontweight='bold')
axes[1, 0].set_ylabel('Number of Events with Tariff Mentions', fontsize=12, fontweight='bold')
axes[1, 0].set_title('Event Count by Quarter', fontsize=14, fontweight='bold')
axes[1, 0].set_xticks(range(len(quarterly_sentiment)))
axes[1, 0].set_xticklabels(quarterly_sentiment.index, rotation=45, ha='right')
axes[1, 0].grid(axis='y', alpha=0.3)

# Plot 4: Share of negative sentiment
axes[1, 1].plot(quarterly_sentiment.index, quarterly_sentiment['Share_Negative'] * 100, 
                marker='D', linewidth=2.5, markersize=10, color='#C73E1D', label='% Negative')
axes[1, 1].set_xlabel('Quarter', fontsize=12, fontweight='bold')
axes[1, 1].set_ylabel('Share of Negative Tariff Sentences (%)', fontsize=12, fontweight='bold')
axes[1, 1].set_title('Negativity Rate Over Time', fontsize=14, fontweight='bold')
axes[1, 1].set_xticks(range(len(quarterly_sentiment)))
axes[1, 1].set_xticklabels(quarterly_sentiment.index, rotation=45, ha='right')
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].legend(fontsize=10)

plt.tight_layout()
output_file = PLOTS_DIR / '8.1_time_series_sentiment.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✓ Saved: {output_file}")
plt.close()

# ============================================================================
# 8.2) Sector heatmap of TariffSent_mean
# ============================================================================
print("\n" + "="*80)
print("8.2) SECTOR HEATMAP")
print("="*80)

# Apply sector from data (obtained via yfinance)
tariff_df_with_tariffs['sector_name'] = tariff_df_with_tariffs['sector'].fillna('Other')

# Sector summary statistics
sector_summary = tariff_df_with_tariffs.groupby('sector_name').agg({
    'TariffSent_mean': ['mean', 'std', 'count'],
    'TariffMentions': 'mean',
    'TariffSent_shareNeg': 'mean'
}).round(4)

sector_summary.columns = ['Avg_Sentiment', 'Std_Sentiment', 'N_Events', 'Avg_Mentions', 'Share_Negative']
sector_summary = sector_summary.sort_values('Avg_Sentiment', ascending=False)

print("\nSector Summary Statistics:")
print(sector_summary.to_string())

# Create pivot table for heatmap
try:
    pivot_sentiment = tariff_df_with_tariffs.pivot_table(
        index='sector_name', 
        columns='year_quarter', 
        values='TariffSent_mean', 
        aggfunc='mean'
    )
    
    # Sort by average sentiment
    pivot_sentiment['avg'] = pivot_sentiment.mean(axis=1)
    pivot_sentiment = pivot_sentiment.sort_values('avg', ascending=False).drop('avg', axis=1)
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(16, 10))
    sns.heatmap(pivot_sentiment, annot=True, fmt='.3f', cmap='RdYlGn', 
                center=0, cbar_kws={'label': 'Average Tariff Sentiment'},
                linewidths=1, linecolor='white', ax=ax,
                vmin=-0.3, vmax=0.3)  # Fixed scale for better comparison
    
    ax.set_title('Sector Heatmap: Average Tariff Sentiment by Quarter', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Quarter', fontsize=13, fontweight='bold')
    ax.set_ylabel('Sector', fontsize=13, fontweight='bold')
    
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    output_file = PLOTS_DIR / '8.2_sector_heatmap.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: {output_file}")
    plt.close()
except Exception as e:
    print(f"\n✗ Could not create sector heatmap: {e}")

# ============================================================================
# 8.3) Word shifts: Negative vs Positive tariff quarters
# ============================================================================
print("\n" + "="*80)
print("8.3) WORD SHIFTS ANALYSIS")
print("="*80)

# Classify events as negative or positive based on median sentiment
median_sentiment = tariff_df_with_tariffs['TariffSent_mean'].median()
tariff_df_with_tariffs['sentiment_category'] = tariff_df_with_tariffs['TariffSent_mean'].apply(
    lambda x: 'Positive' if x > median_sentiment else 'Negative'
)

print(f"\nMedian tariff sentiment: {median_sentiment:.4f}")
print(f"Negative events: {(tariff_df_with_tariffs['sentiment_category'] == 'Negative').sum()}")
print(f"Positive events: {(tariff_df_with_tariffs['sentiment_category'] == 'Positive').sum()}")

# Extract keywords from tariff sentences
def extract_keywords_from_sentences(sentences_list):
    """Extract keywords from list of sentence lists"""
    all_words = []
    for sentences in sentences_list:
        if isinstance(sentences, list):
            for sent in sentences:
                # Simple tokenization and cleaning
                words = re.findall(r'\b[a-z]{4,}\b', sent.lower())
                # Filter out common stop words
                stop_words = {
                    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 
                    'has', 'had', 'was', 'were', 'are', 'been', 'being', 'our',
                    'their', 'will', 'would', 'could', 'should', 'can', 'may',
                    'they', 'them', 'these', 'those', 'there', 'where', 'when',
                    'which', 'what', 'some', 'more', 'very', 'about', 'into',
                    'through', 'than', 'also', 'just', 'only', 'other', 'such'
                }
                words = [w for w in words if w not in stop_words]
                all_words.extend(words)
    return Counter(all_words)

# Get keywords for negative and positive events
negative_sentences = tariff_df_with_tariffs[
    tariff_df_with_tariffs['sentiment_category'] == 'Negative'
]['tariff_sentences'].tolist()

positive_sentences = tariff_df_with_tariffs[
    tariff_df_with_tariffs['sentiment_category'] == 'Positive'
]['tariff_sentences'].tolist()

negative_keywords = extract_keywords_from_sentences(negative_sentences)
positive_keywords = extract_keywords_from_sentences(positive_sentences)

print("\nTop 20 Keywords in NEGATIVE Events:")
for word, count in negative_keywords.most_common(20):
    print(f"  {word:20} : {count:5d}")

print("\nTop 20 Keywords in POSITIVE Events:")
for word, count in positive_keywords.most_common(20):
    print(f"  {word:20} : {count:5d}")

# Create word shift visualization
try:
    # Get top words from both categories
    top_neg_words = set([w for w, c in negative_keywords.most_common(30)])
    top_pos_words = set([w for w, c in positive_keywords.most_common(30)])
    all_top_words = top_neg_words.union(top_pos_words)
    
    # Normalize by total words
    total_neg = sum(negative_keywords.values())
    total_pos = sum(positive_keywords.values())
    
    word_comparison = pd.DataFrame({
        'word': list(all_top_words),
        'neg_freq': [negative_keywords.get(w, 0) / total_neg * 1000 for w in all_top_words],
        'pos_freq': [positive_keywords.get(w, 0) / total_pos * 1000 for w in all_top_words]
    })
    
    # Calculate difference
    word_comparison['diff'] = word_comparison['neg_freq'] - word_comparison['pos_freq']
    word_comparison = word_comparison.sort_values('diff', ascending=True).tail(30)  # Top 30 for better viz
    
    # Create horizontal bar chart
    fig, ax = plt.subplots(figsize=(12, 10))
    colors = ['darkred' if x > 0 else 'darkgreen' for x in word_comparison['diff']]
    
    y_pos = np.arange(len(word_comparison))
    ax.barh(y_pos, word_comparison['diff'], color=colors, alpha=0.7, edgecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(word_comparison['word'], fontsize=11)
    ax.set_xlabel('Frequency Difference (per 1000 words)', fontsize=13, fontweight='bold')
    ax.set_title('Word Shifts: Negative vs Positive Tariff Events\n' + 
                 'Red = More in Negative | Green = More in Positive', 
                 fontsize=14, fontweight='bold', pad=15)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=2)
    ax.grid(axis='x', alpha=0.3)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='darkred', alpha=0.7, label='More in Negative Events'),
        Patch(facecolor='darkgreen', alpha=0.7, label='More in Positive Events')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=11)
    
    plt.tight_layout()
    output_file = PLOTS_DIR / '8.3_word_shifts.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved: {output_file}")
    plt.close()
except Exception as e:
    print(f"\n✗ Could not create word shifts plot: {e}")

# ============================================================================
# 8.4) Sentiment distribution and patterns
# ============================================================================
print("\n" + "="*80)
print("8.4) SENTIMENT DISTRIBUTION & PATTERNS")
print("="*80)

# Statistical summary
print("\nTariff Sentiment Statistics:")
print(tariff_df_with_tariffs['TariffSent_mean'].describe().to_string())

# Create 4-panel visualization
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Panel 1: Histogram of sentiment
axes[0, 0].hist(tariff_df_with_tariffs['TariffSent_mean'], bins=40, 
                color='steelblue', edgecolor='black', alpha=0.7)
axes[0, 0].axvline(x=0, color='red', linestyle='--', linewidth=2, label='Neutral', alpha=0.7)
axes[0, 0].axvline(x=tariff_df_with_tariffs['TariffSent_mean'].median(), 
                   color='green', linestyle='--', linewidth=2, label='Median', alpha=0.7)
axes[0, 0].axvline(x=tariff_df_with_tariffs['TariffSent_mean'].mean(), 
                   color='orange', linestyle='--', linewidth=2, label='Mean', alpha=0.7)
axes[0, 0].set_xlabel('Tariff Sentiment', fontsize=12, fontweight='bold')
axes[0, 0].set_ylabel('Frequency', fontsize=12, fontweight='bold')
axes[0, 0].set_title('Distribution of Tariff Sentiment', fontsize=13, fontweight='bold')
axes[0, 0].legend(fontsize=10)
axes[0, 0].grid(alpha=0.3, axis='y')

# Panel 2: Sentiment vs Mentions scatter
axes[0, 1].scatter(tariff_df_with_tariffs['TariffMentions'], 
                   tariff_df_with_tariffs['TariffSent_mean'],
                   alpha=0.4, s=50, c=tariff_df_with_tariffs['TariffSent_mean'],
                   cmap='RdYlGn', edgecolors='black', linewidth=0.5)
axes[0, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=2)
axes[0, 1].set_xlabel('Number of Tariff Mentions', fontsize=12, fontweight='bold')
axes[0, 1].set_ylabel('Tariff Sentiment', fontsize=12, fontweight='bold')
axes[0, 1].set_title('Sentiment vs Mention Frequency', fontsize=13, fontweight='bold')
axes[0, 1].grid(alpha=0.3)

# Add correlation
corr = tariff_df_with_tariffs[['TariffMentions', 'TariffSent_mean']].corr().iloc[0, 1]
axes[0, 1].text(0.05, 0.95, f'Correlation: {corr:.3f}', 
                transform=axes[0, 1].transAxes, fontsize=11,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Panel 3: Box plot by category
sentiment_by_cat = [
    tariff_df_with_tariffs[tariff_df_with_tariffs['sentiment_category'] == 'Negative']['TariffSent_mean'],
    tariff_df_with_tariffs[tariff_df_with_tariffs['sentiment_category'] == 'Positive']['TariffSent_mean']
]
bp = axes[1, 0].boxplot(sentiment_by_cat, labels=['Negative', 'Positive'], 
                        patch_artist=True, widths=0.6)
for patch, color in zip(bp['boxes'], ['lightcoral', 'lightgreen']):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
axes[1, 0].axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=2)
axes[1, 0].set_ylabel('Tariff Sentiment', fontsize=12, fontweight='bold')
axes[1, 0].set_title('Sentiment by Category', fontsize=13, fontweight='bold')
axes[1, 0].grid(alpha=0.3, axis='y')

# Panel 4: Quarterly trend with error bars
quarterly_with_std = tariff_df_with_tariffs.groupby('year_quarter').agg({
    'TariffSent_mean': ['mean', 'std', 'count']
})
quarterly_with_std.columns = ['mean', 'std', 'count']
quarterly_with_std = quarterly_with_std.sort_index()

x_pos = range(len(quarterly_with_std))
axes[1, 1].errorbar(x_pos, quarterly_with_std['mean'], 
                    yerr=quarterly_with_std['std'],
                    marker='o', linewidth=2.5, markersize=8, capsize=6, capthick=2,
                    color='#2E86AB', ecolor='gray', alpha=0.8)
axes[1, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5, linewidth=2, label='Neutral')
axes[1, 1].set_xticks(x_pos)
axes[1, 1].set_xticklabels(quarterly_with_std.index, rotation=45, ha='right')
axes[1, 1].set_xlabel('Quarter', fontsize=12, fontweight='bold')
axes[1, 1].set_ylabel('Tariff Sentiment', fontsize=12, fontweight='bold')
axes[1, 1].set_title('Quarterly Sentiment with Standard Deviation', fontsize=13, fontweight='bold')
axes[1, 1].legend(fontsize=10)
axes[1, 1].grid(alpha=0.3)

plt.tight_layout()
output_file = PLOTS_DIR / '8.4_sentiment_analysis.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✓ Saved: {output_file}")
plt.close()

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*80)
print("REQUIREMENT 8 COMPLETE!")
print("="*80)
print(f"\n✓ Generated 4 high-resolution visualizations in {PLOTS_DIR}:")
print(f"  1. 8.1_time_series_sentiment.png")
print(f"  2. 8.2_sector_heatmap.png")
print(f"  3. 8.3_word_shifts.png")
print(f"  4. 8.4_sentiment_analysis.png")

print(f"\n📊 Key Findings:")
print(f"  - Overall average sentiment: {tariff_df_with_tariffs['TariffSent_mean'].mean():.4f}")
print(f"  - Sentiment std deviation: {tariff_df_with_tariffs['TariffSent_mean'].std():.4f}")
print(f"  - Most negative sector: {sector_summary.iloc[-1].name} ({sector_summary.iloc[-1]['Avg_Sentiment']:.4f})")
print(f"  - Most positive sector: {sector_summary.iloc[0].name} ({sector_summary.iloc[0]['Avg_Sentiment']:.4f})")
print(f"  - Average mentions per event: {tariff_df_with_tariffs['TariffMentions'].mean():.2f}")
print(f"  - Quarters analyzed: {len(quarterly_sentiment)}")

print("\n" + "="*80)
