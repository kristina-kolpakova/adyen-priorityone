import pandas as pd

from gong import red_flag_map

# --- Load Slack Data ---

# Messages from shared customer channels, in Slack's export columns.
slack = pd.read_csv("data/slack_messages.csv", dtype={"ts": str, "thread_ts": str})

# Slack doesn't know Salesforce accounts, so each shared channel is mapped to one.
channels = pd.read_csv("data/slack_channels.csv")
slack = slack.merge(channels[["channel_id", "account_id"]], on="channel_id", how="inner")

# Slack timestamps are seconds since 1970 (UTC); convert them to dates.
slack["sent_at"] = pd.to_datetime(slack["ts"].astype(float), unit="s")
slack["MessageDate"] = slack["sent_at"].dt.normalize()

# A reply belongs to its thread; a message without one starts its own thread.
slack["thread"] = slack["thread_ts"].fillna(slack["ts"])

# Messages from Adyen's own workspace are ours; everything else is the customer.
ADYEN_TEAM = "T0ADYEN01"
slack["from_customer"] = slack["team"] != ADYEN_TEAM

# A stable evidence ID per message, and a mock link to it.
slack["message_id"] = "slack-" + slack["channel_id"] + "-" + slack["ts"].str.replace(".", "", regex=False)
slack["url"] = (
    "https://slack.example.invalid/archives/" + slack["channel_id"]
    + "/p" + slack["ts"].str.replace(".", "", regex=False)
)


# --- Red Flag Classification ---

# The same categories as Gong, plus four that only show up in written chat.
slack_red_flag_map = {
    **red_flag_map,

    # Live payment problems raised in the channel
    "checkout is failing": "Service incident",
    "is something down": "Service incident",
    "outage": "Service incident",

    # The main contact leaving
    "my last day": "Champion departure",
    "leaving the company": "Champion departure",

    # Disagreements about invoices or fees
    "invoice doesn't match": "Billing dispute",
    "charged twice": "Billing dispute",
}


# Assign one category to each customer message; our own messages aren't red flags.
def classify_message(text):
    for phrase, category in slack_red_flag_map.items():
        if phrase in text.lower():
            return category

    return None


slack["red_flag"] = None
slack.loc[slack["from_customer"], "red_flag"] = slack.loc[slack["from_customer"], "text"].apply(classify_message)


# --- Last Message in Each Thread ---

# For "Unanswered request": who spoke last in each thread, and when. integration.py
# flags threads where the customer asked a question and is still waiting on us.
last_in_thread = (
    slack.sort_values("sent_at")
    .drop_duplicates(subset=["channel_id", "thread"], keep="last")
    .copy()
)
