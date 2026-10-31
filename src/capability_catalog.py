"""Reusable sample capability descriptions for CLI and pipeline discovery."""

from typing import Any


CAPABILITY_CATALOG = (
    (
        "Customer Financial Balance Management",
        "This capability manages customer account balances, evaluates yearly "
        "expenditures, updates VIP tiers, and calculates monthly interest. "
        "Weekly billing and month-end processing maintain accurate customer "
        "ledgers and accrued interest.",
    ),
    (
        "Customer Payments and Transfers",
        "This capability validates customer payments, authorizes eligible "
        "transactions, and posts approved payments to account ledgers. "
        "Scheduled payment processing maintains payment status and balances.",
    ),
    (
        "Loan Servicing and Interest Accrual",
        "This capability applies borrower payments to outstanding loan "
        "principal, tracks delinquent accounts, and accrues daily interest "
        "using contractual rates to keep loan balances current.",
    ),
    (
        "Card Authorization and Settlement",
        "This capability evaluates card transactions against card status and "
        "available credit, authorizes or declines purchases, and settles "
        "approved transactions during the card settlement cycle.",
    ),
    (
        "Insurance Claims Adjudication",
        "This capability validates insurance claims against policy status, "
        "assigns processing status, calculates reserves for eligible claims, "
        "and records adjustments for downstream review.",
    ),
    (
        "Regulatory Reporting and AML Compliance",
        "This capability screens high-value transactions for anti-money "
        "laundering review, reconciles daily transaction totals, and prepares "
        "controlled data for regulatory reporting.",
    ),
    (
        "Customer Onboarding and KYC Verification",
        "This capability creates customer profiles, validates identity and "
        "compliance documents, and activates accounts after know-your-customer "
        "checks using shared customer records and audit logging.",
    ),
    (
        "Treasury Cash Position and Forecasting",
        "This capability consolidates posted payment and card settlement "
        "activity into the daily cash position, then forecasts near-term "
        "liquidity using balances and scheduled payment obligations.",
    ),
)


def seed_capability_catalog(discovery_service: Any, top_k: int = 2) -> None:
  """Embed and tag each sample capability before ranked capability search."""
  for capability_name, capability_summary in CAPABILITY_CATALOG:
    discovery_service.discover_and_tag(
        capability_name, capability_summary, top_k=top_k
    )
