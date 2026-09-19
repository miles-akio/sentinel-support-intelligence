"""
generate_raw_tickets.py
------------------------
Simulates a raw extract of customer support tickets, the way it would come
out of Zendesk/Intercom/Freshdesk. Each ticket has real (templated) natural
language text, which is what makes the LLM enrichment step downstream
meaningful — this isn't just numeric data, it's unstructured text that needs
an LLM (not a simple rule) to classify, score, and summarize.

Run:
    python ingestion/generate_raw_tickets.py
"""

import random
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
from faker import Faker

fake = Faker()
Faker.seed(7)
random.seed(7)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

N_CUSTOMERS = 300
N_TICKETS = 400

# Realistic ticket bodies grouped by the TRUE underlying issue (kept hidden
# from the pipeline — this is our "ground truth" to compare the LLM against).
TEMPLATES = {
    "billing": [
        "I was charged twice for my {plan} subscription this month. Can you refund the duplicate charge?",
        "My invoice shows a price increase I wasn't notified about. Why did my {plan} plan go up in price?",
        "I cancelled my account last week but was still billed for {plan}. Please refund me immediately.",
        "The discount code I used didn't apply at checkout for my {plan} order. I was overcharged.",
    ],
    "bug": [
        "The app crashes every time I try to open the {feature} screen on my phone.",
        "I'm getting a blank white screen after updating to the latest version, specifically in {feature}.",
        "Uploading a file to {feature} fails with an error every single time, no matter the file size.",
        "The {feature} page has been stuck loading for over 10 minutes now.",
    ],
    "account_access": [
        "I can't log into my account, it keeps saying my password is incorrect even after resetting it.",
        "I never received the two-factor authentication code to log in, I'm locked out.",
        "My account got suspended with no explanation and I need access back for {feature}.",
        "I'm trying to change my email address but the verification link isn't working.",
    ],
    "feature_request": [
        "It would be really helpful if {feature} supported exporting to CSV.",
        "Could you add dark mode support to {feature}? Would make a big difference for me.",
        "Please consider adding bulk editing to {feature}, doing it one at a time is painful.",
        "A mobile app version of {feature} would massively improve my workflow.",
    ],
    "shipping": [
        "My order still hasn't arrived and it's been 2 weeks past the estimated delivery date.",
        "The tracking number for my order shows no updates for 5 days now.",
        "I received the wrong item in my package, I ordered something completely different.",
        "My package arrived damaged, the box was crushed and the product inside is broken.",
    ],
}

URGENT_PHRASES = [
    "This is extremely urgent, ",
    "I need this resolved immediately, ",
    "This is unacceptable and I want a resolution today. ",
    "",
    "",
    "",
]

FEATURES = ["the dashboard", "the reports tab", "checkout", "the mobile app", "settings", "the search bar"]
PLANS = ["Pro", "Team", "Enterprise", "Starter"]


def generate_customers() -> pl.DataFrame:
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        rows.append(
            {
                "customer_id": i,
                "customer_name": fake.name(),
                "email": fake.email(),
                "plan": random.choice(PLANS),
                "signup_date": fake.date_between(start_date="-2y", end_date="-30d").isoformat(),
            }
        )
    return pl.DataFrame(rows)


def generate_tickets() -> pl.DataFrame:
    start = datetime(2026, 6, 1)
    rows = []
    for ticket_id in range(1, N_TICKETS + 1):
        true_category = random.choice(list(TEMPLATES.keys()))
        template = random.choice(TEMPLATES[true_category])
        body = template.format(feature=random.choice(FEATURES), plan=random.choice(PLANS))
        body = random.choice(URGENT_PHRASES) + body

        rows.append(
            {
                "ticket_id": ticket_id,
                "customer_id": random.randint(1, N_CUSTOMERS),
                "created_at": (start + timedelta(hours=random.randint(0, 24 * 45))).strftime("%Y-%m-%d %H:%M:%S"),
                "subject": body.split(".")[0][:60],
                "body": body,
                "true_category": true_category,  # kept only for eval purposes, not used by the pipeline
            }
        )
    return pl.DataFrame(rows)


if __name__ == "__main__":
    customers = generate_customers()
    tickets = generate_tickets()

    customers.write_csv(RAW_DIR / "customers.csv")
    tickets.write_csv(RAW_DIR / "tickets.csv")

    print(f"customers: {customers.shape}")
    print(f"tickets:   {tickets.shape}")
    print(f"Raw CSVs written to: {RAW_DIR}")
