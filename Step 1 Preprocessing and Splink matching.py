#1 Preprocessing and Splink-based probabilistic matching

import pandas as pd
import unidecode
from nameparser import HumanName
import nicknames
from splink import Splink
from splink.duckdb.duckdb_linker import DuckDBLinker

# ========== LOAD DATA ==========
df1 = pd.read_csv("dataset_a.csv")
df2 = pd.read_csv("dataset_b.csv")

# Add dataset identifiers
df1['dataset'] = 'A'
df2['dataset'] = 'B'

# ========== PREPROCESSING ==========
def normalize_nickname(name):
    """Normalize nicknames to canonical names"""
    if pd.isnull(name) or name.strip() == "":
        return ""
    name_lower = name.strip().lower()
    return nicknames.canonical_name(name_lower) or name_lower

def clean_name_parts(first, last, full=None):
    """Clean and normalize names"""
    if pd.notnull(full) and full.strip() != "":
        parsed = HumanName(unidecode.unidecode(full))
    else:
        parsed = HumanName(f"{first} {last}")
    first_clean = normalize_nickname(parsed.first)
    last_clean = parsed.last.lower()
    return f"{first_clean} {last_clean}".strip()

def clean_npi(npi):
    """Clean NPI: keep only digits"""
    if pd.isnull(npi):
        return ''
    return ''.join(filter(str.isdigit, str(npi)))

def clean_state(state):
    """Standardize U.S. state abbreviations"""
    if pd.isnull(state):
        return ''
    return state.strip().upper()

# Clean Dataset A
df1['clean_name'] = df1.apply(
    lambda row: clean_name_parts(row['first_name'], row['last_name'], row.get('full_name', None)),
    axis=1
)
df1['clean_npi'] = df1['npi'].apply(clean_npi)
df1['clean_state'] = df1['mailing_state'].apply(clean_state)

# Clean Dataset B
df2['clean_name'] = df2.apply(
    lambda row: clean_name_parts(row['first_name'], row['last_name']),
    axis=1
)
df2['clean_npi'] = df2['npi'].apply(clean_npi)

# Combine mailing and license states for multi-state overlap
def combine_states(row):
    states = []
    if pd.notnull(row['mailing_state']):
        states.append(clean_state(row['mailing_state']))
    if pd.notnull(row['license_state']):
        states.append(clean_state(row['license_state']))
    return states

df2['all_states'] = df2.apply(combine_states, axis=1)

# Combine datasets for Splink
combined_df = pd.concat([df1, df2], ignore_index=True)

# ========== SPLINK CONFIGURATION ==========
settings = {
    "link_type": "link_only",
    "comparisons": [
        {
            "output_column_name": "name_similarity",
            "comparison_levels": [
                {"level": "exact"},
                {"level": "levenshtein", "threshold": 0.8},
                {"level": "else"}
            ],
            "input_columns": ["clean_name", "clean_name"]
        },
        {
            "output_column_name": "npi_match",
            "comparison_levels": [
                {"level": "exact"},
                {"level": "else"}
            ],
            "input_columns": ["clean_npi", "clean_npi"]
        },
        {
            "output_column_name": "state_overlap",
            "comparison_levels": [
                {"sql_condition": "l.clean_state = ANY(r.all_states)", "label": "state_overlap"},
                {"sql_condition": "l.clean_state != ANY(r.all_states)", "label": "state_mismatch"},
                {"sql_condition": "TRUE", "label": "missing_state"}
            ],
            "input_columns": ["clean_state", "all_states"]
        }
    ],
    "blocking_rules_to_generate_predictions": [
        "l.clean_state = ANY(r.all_states)",  # Block on any state overlap
        "l.clean_name LIKE r.clean_name || '%'"  # Secondary blocking
    ],
    "retain_intermediate_calculation_columns": True
}

# ========== RUN SPLINK ==========
linker = DuckDBLinker(combined_df, settings)

# Train Splink
linker.estimate_u_using_random_sampling(max_pairs=1e6)
linker.estimate_parameters_using_expectation_maximisation()

# Predict matches
df_matches = linker.predict()

# Save all matches
df_matches.to_csv("splink_matched_physicians_multi_state.csv", index=False)
print("✅ All matches saved: 'splink_matched_physicians_multi_state.csv'")