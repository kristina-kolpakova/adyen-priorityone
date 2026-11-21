import pandas as pd


# --- Account Scores by Opportunity Type ---

def score_types(opportunities):
    """Each account's highest opportunity score, separately for each type."""

    # Separate opportunities by type.
    renewals = opportunities[opportunities["Type"] == "Renewal"]
    upsell_new = opportunities[opportunities["Type"].isin(["Upsell", "New"])]

    # The highest-scoring opportunity of each type, per account.
    renewal_scores = renewals.groupby("AccountName")["PriorityScore"].max()
    upsell_new_scores = upsell_new.groupby("AccountName")["PriorityScore"].max()

    # Combine both scores into one table; accounts with no deals of a type get 0.
    type_scores = pd.DataFrame({
        "RenewalScore": renewal_scores,
        "UpsellNewScore": upsell_new_scores
    }).fillna(0)

    return type_scores
