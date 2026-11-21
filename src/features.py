"""Build the modelling table: one row per loan application with customer,
bureau and transaction features joined on."""
import os

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import create_engine

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2:///credit_risk")

NUMERIC = [
    # customer
    "age", "dependents", "years_at_residence", "annual_income", "tenure_years",
    # bureau
    "credit_score", "num_open_accounts", "num_credit_inquiries_6m",
    "credit_utilization_ratio", "num_late_payments_30d", "num_late_payments_90d",
    "num_defaults_prior", "bankruptcies", "oldest_account_age_months", "debt_to_limit",
    # application
    "requested_amount", "loan_term_months", "interest_rate", "debt_to_income_ratio",
    "loan_to_income", "collateral_flag",
    # transactions
    "total_inflow", "total_outflow", "net_cash_flow", "emi_outflow",
    "avg_balance", "txn_count", "inflow_outflow_ratio",
]
CATEGORICAL = ["loan_type", "employment_type", "education", "residence_type", "marital_status"]
TARGET = "loan_default"


def load_tables():
    engine = create_engine(DB_URL)
    customers = pd.read_sql("SELECT * FROM customers", engine, parse_dates=["customer_since"])
    # contact details never go into the model
    customers = customers.drop(columns=["first_name", "last_name", "email", "phone"])
    credit = pd.read_sql("SELECT * FROM credit_history", engine)
    loans = pd.read_sql("SELECT * FROM loan_applications", engine, parse_dates=["application_date"])
    txns = pd.read_sql("SELECT * FROM transactions", engine)
    return customers, credit, loans, txns


def transaction_features(txns):
    """Roll transactions up to one row per customer."""
    t = txns.copy()
    t["inflow"] = np.where(t["transaction_type"] == "Credit", t["amount"], 0)
    t["outflow"] = np.where(t["transaction_type"] == "Debit", t["amount"], 0)
    t["emi"] = np.where(t["category"] == "EMI", t["amount"], 0)

    agg = t.groupby("customer_id").agg(
        total_inflow=("inflow", "sum"),
        total_outflow=("outflow", "sum"),
        emi_outflow=("emi", "sum"),
        avg_balance=("balance_after", "mean"),
        txn_count=("transaction_id", "count"),
    )
    agg["net_cash_flow"] = agg["total_inflow"] - agg["total_outflow"]
    agg["inflow_outflow_ratio"] = agg["total_inflow"] / agg["total_outflow"].replace(0, np.nan)
    return agg.reset_index()


def build_features(customers, credit, loans, txns):
    """One row per application. Columns only known after the decision are left out."""
    leak_cols = ["approval_status", "approved_amount", "decision_date", "disbursed_flag"]

    df = (loans.drop(columns=leak_cols)
               .merge(customers, on="customer_id", how="left")
               .merge(credit, on="customer_id", how="left")
               .merge(transaction_features(txns), on="customer_id", how="left"))

    # some applications are dated before customer_since, treat those as 0
    df["tenure_years"] = ((df["application_date"] - df["customer_since"]).dt.days / 365.25).clip(lower=0)
    df["debt_to_limit"] = df["total_outstanding_debt"] / df["total_credit_limit"].replace(0, np.nan)
    df["loan_to_income"] = df["requested_amount"] / df["annual_income"].replace(0, np.nan)

    for col in CATEGORICAL:
        df[col] = df[col].fillna("Unknown")

    return df[["application_id", "customer_id"] + NUMERIC + CATEGORICAL + [TARGET]]


def modelling_data():
    """Features for disbursed loans only, since that's where we know the outcome."""
    df = build_features(*load_tables())
    df = df[df[TARGET].notna()].reset_index(drop=True)
    df[TARGET] = df[TARGET].astype(int)
    return df


def make_preprocessor(scale=False):
    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scale", StandardScaler()))

    cat_steps = [
        ("impute", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ]
    return ColumnTransformer([
        ("num", Pipeline(num_steps), NUMERIC),
        ("cat", Pipeline(cat_steps), CATEGORICAL),
    ])
