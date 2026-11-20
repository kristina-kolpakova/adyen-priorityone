import pandas as pd


# --- Account Priority Score ---

def score_accounts(opportunities):
    """Combine opportunity scores into one priority score per account.

    Returns the opportunities with each one's rank and contribution, and the
    total priority score for each account.
    """
    opportunities = opportunities.copy()

    # Rank opportunities within each account, highest score first.
    opportunities["OpportunityRank"] = (
        opportunities.groupby("AccountName")["PriorityScore"]
        .rank(method="first", ascending=False)
    )

    # Initialize each opportunity's contribution to its account score.
    opportunities["AccountContribution"] = 0.0

    # Count the highest-scoring opportunity at 100%.
    opportunities.loc[
        opportunities["OpportunityRank"] == 1, "AccountContribution"
    ] = opportunities["PriorityScore"]

    # Count additional current-quarter and overdue opportunities at 50%.
    opportunities.loc[
        (opportunities["OpportunityRank"] > 1) & (opportunities["QuartersAway"] <= 0),
        "AccountContribution"
    ] = opportunities["PriorityScore"] * 0.5

    # Count additional next-quarter opportunities at 25%.
    opportunities.loc[
        (opportunities["OpportunityRank"] > 1) & (opportunities["QuartersAway"] == 1),
        "AccountContribution"
    ] = opportunities["PriorityScore"] * 0.25

    # Count additional later-quarter opportunities at 10%.
    opportunities.loc[
        (opportunities["OpportunityRank"] > 1) & (opportunities["QuartersAway"] >= 2),
        "AccountContribution"
    ] = opportunities["PriorityScore"] * 0.10

    # Sum opportunity contributions to calculate each account's priority.
    account_scores = (
        opportunities.groupby("AccountName")["AccountContribution"].sum()
    )

    return opportunities, account_scores


# --- Account Scores by Opportunity Type ---

def score_types(opportunities):

    # Separate opportunities by type.
    renewals = opportunities[opportunities["Type"] == "Renewal"]
    upsell_new = opportunities[opportunities["Type"].isin(["Upsell", "New"])]

    # Calculate account scores for each group.
    _, renewal_scores = score_accounts(renewals)
    _, upsell_new_scores = score_accounts(upsell_new)

    # Combine both scores into one table.
    type_scores = pd.DataFrame({
        "RenewalScore": renewal_scores,
        "UpsellNewScore": upsell_new_scores
    }).fillna(0)

    return type_scores
