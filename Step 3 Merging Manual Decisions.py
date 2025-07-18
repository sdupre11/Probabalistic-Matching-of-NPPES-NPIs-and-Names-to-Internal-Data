#3 Merging Manual Decisions Post-Merge.
##NOTE: The decisions have been made by the reviewer manually completing the Decision column in the Excel file generated during Step 2: Create Excel...

# Load reviewed file
reviewed_file = "splink_ambiguous_matches_reviewer_friendly.xlsx"
splink_all_matches = "splink_matched_physicians_multi_state.csv"
reviewed_df = pd.read_excel(reviewed_file)
all_matches_df = pd.read_csv(splink_all_matches)

# Split reviewed matches
accepted = reviewed_df[reviewed_df["Decision"].str.lower() == "accept"]
rejected = reviewed_df[reviewed_df["Decision"].str.lower() == "reject"]
to_review = reviewed_df[reviewed_df["Decision"].str.lower() == "review later"]

# Final approved matches
clean_matches = all_matches_df[~all_matches_df['unique_id_l'].isin(reviewed_df['unique_id_l'])]
final_matches = pd.concat([clean_matches, accepted], ignore_index=True)
final_matches.to_csv("splink_final_approved_matches.csv", index=False)
print(f"✅ Final approved matches saved: 'splink_final_approved_matches.csv'")

# Save rejected and unresolved
if not rejected.empty:
    rejected.to_csv("splink_rejected_matches.csv", index=False)
    print("❌ Rejected matches saved: 'splink_rejected_matches.csv'")
if not to_review.empty:
    to_review.to_csv("splink_unresolved_matches.csv", index=False)
    print("🕒 Unresolved matches saved: 'splink_unresolved_matches.csv'")