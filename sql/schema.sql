-- =====================================================================
-- Credora Finance | Credit Risk & Loan Approval Analytics Platform
-- Tables, constraints and indexes
-- Target engine: PostgreSQL 14+  (MySQL 8+ compatible with minor edits)
-- Owner: Data & Analytics Team, Credora Finance
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. Clean start (safe re-run)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS transactions      CASCADE;
DROP TABLE IF EXISTS loan_applications CASCADE;
DROP TABLE IF EXISTS credit_history    CASCADE;
DROP TABLE IF EXISTS customers         CASCADE;

-- ---------------------------------------------------------------------
-- 1. DDL : CUSTOMERS  (parent table)
-- ---------------------------------------------------------------------
CREATE TABLE customers (
    customer_id         VARCHAR(12)   PRIMARY KEY,
    first_name          VARCHAR(50)   NOT NULL,
    last_name           VARCHAR(50)   NOT NULL,
    gender              VARCHAR(10)   CHECK (gender IN ('Male','Female','Other')),
    date_of_birth       DATE          NOT NULL,
    age                 SMALLINT      CHECK (age BETWEEN 18 AND 100),
    marital_status      VARCHAR(15),
    dependents          SMALLINT      DEFAULT 0 CHECK (dependents >= 0),
    education           VARCHAR(30),
    employment_type     VARCHAR(20),
    occupation          VARCHAR(60),
    annual_income       NUMERIC(12,2) CHECK (annual_income >= 0),
    city                VARCHAR(50),
    state               VARCHAR(50),
    residence_type      VARCHAR(20),
    years_at_residence  SMALLINT      CHECK (years_at_residence >= 0),
    email               VARCHAR(120),
    phone               VARCHAR(20),
    kyc_status          VARCHAR(15)   DEFAULT 'Pending'
                                      CHECK (kyc_status IN ('Verified','Pending','Rejected')),
    customer_since      DATE          NOT NULL
);

-- ---------------------------------------------------------------------
-- 2. DDL : CREDIT_HISTORY  (1:1 with customer, bureau snapshot)
-- ---------------------------------------------------------------------
CREATE TABLE credit_history (
    credit_id                 VARCHAR(12)   PRIMARY KEY,
    customer_id               VARCHAR(12)   NOT NULL UNIQUE,
    as_of_date                DATE          NOT NULL,
    credit_score              SMALLINT      CHECK (credit_score BETWEEN 300 AND 900),
    num_open_accounts         SMALLINT      CHECK (num_open_accounts >= 0),
    num_credit_inquiries_6m   SMALLINT      CHECK (num_credit_inquiries_6m >= 0),
    credit_utilization_ratio  NUMERIC(4,3)  CHECK (credit_utilization_ratio BETWEEN 0 AND 1),
    num_late_payments_30d     SMALLINT      DEFAULT 0,
    num_late_payments_90d     SMALLINT      DEFAULT 0,
    num_defaults_prior        SMALLINT      DEFAULT 0,
    bankruptcies              SMALLINT      DEFAULT 0,
    total_credit_limit        NUMERIC(12,2) CHECK (total_credit_limit >= 0),
    total_outstanding_debt    NUMERIC(12,2) CHECK (total_outstanding_debt >= 0),
    oldest_account_age_months SMALLINT      CHECK (oldest_account_age_months >= 0),
    CONSTRAINT fk_credit_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 3. DDL : LOAN_APPLICATIONS  (many:1 with customer, holds ML target)
-- ---------------------------------------------------------------------
CREATE TABLE loan_applications (
    application_id           VARCHAR(12)   PRIMARY KEY,
    customer_id              VARCHAR(12)   NOT NULL,
    application_date         DATE          NOT NULL,
    loan_type                VARCHAR(20)   NOT NULL,
    loan_purpose             VARCHAR(50),
    requested_amount         NUMERIC(12,2) CHECK (requested_amount > 0),
    loan_term_months         SMALLINT      CHECK (loan_term_months > 0),
    interest_rate            NUMERIC(5,2)  CHECK (interest_rate >= 0),
    applicant_monthly_income NUMERIC(12,2) CHECK (applicant_monthly_income >= 0),
    existing_emi             NUMERIC(12,2) DEFAULT 0,
    debt_to_income_ratio     NUMERIC(5,3)  CHECK (debt_to_income_ratio >= 0),
    collateral_flag          SMALLINT      DEFAULT 0 CHECK (collateral_flag IN (0,1)),
    approval_status          VARCHAR(15)   NOT NULL
                                           CHECK (approval_status IN ('Approved','Rejected','Under Review')),
    approved_amount          NUMERIC(12,2) DEFAULT 0,
    decision_date            DATE,
    disbursed_flag           SMALLINT      DEFAULT 0 CHECK (disbursed_flag IN (0,1)),
    loan_default             SMALLINT      CHECK (loan_default IN (0,1)),   -- NULL for non-disbursed
    CONSTRAINT fk_loan_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    CONSTRAINT chk_decision_after_application
        CHECK (decision_date IS NULL OR decision_date >= application_date)
);

-- ---------------------------------------------------------------------
-- 4. DDL : TRANSACTIONS  (many:1 with customer, behavioural signal)
-- ---------------------------------------------------------------------
CREATE TABLE transactions (
    transaction_id     VARCHAR(14)   PRIMARY KEY,
    customer_id        VARCHAR(12)   NOT NULL,
    transaction_date   DATE          NOT NULL,
    transaction_type   VARCHAR(10)   CHECK (transaction_type IN ('Credit','Debit')),
    category           VARCHAR(30),
    channel            VARCHAR(20),
    amount             NUMERIC(12,2) CHECK (amount >= 0),
    balance_after      NUMERIC(12,2),
    CONSTRAINT fk_txn_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 5. INDEXES  (query-path optimisation for analytics & joins)
-- ---------------------------------------------------------------------
CREATE INDEX idx_credit_customer      ON credit_history (customer_id);
CREATE INDEX idx_credit_score         ON credit_history (credit_score);
CREATE INDEX idx_loan_customer        ON loan_applications (customer_id);
CREATE INDEX idx_loan_status          ON loan_applications (approval_status);
CREATE INDEX idx_loan_appdate         ON loan_applications (application_date);
CREATE INDEX idx_loan_default         ON loan_applications (loan_default);
CREATE INDEX idx_txn_customer         ON transactions (customer_id);
CREATE INDEX idx_txn_date             ON transactions (transaction_date);
CREATE INDEX idx_txn_category         ON transactions (category);

