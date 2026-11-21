-- Analytical queries (run after loading the data)

-- 7.1  Credit score analysis: distribution across standard risk bands
SELECT
    CASE
        WHEN credit_score >= 750 THEN 'Excellent (750-900)'
        WHEN credit_score >= 700 THEN 'Good (700-749)'
        WHEN credit_score >= 650 THEN 'Fair (650-699)'
        WHEN credit_score >= 580 THEN 'Poor (580-649)'
        ELSE 'Very Poor (300-579)'
    END                                   AS credit_band,
    COUNT(*)                              AS customers,
    ROUND(AVG(credit_score),0)            AS avg_score,
    ROUND(AVG(credit_utilization_ratio),3) AS avg_utilization,
    ROUND(AVG(num_late_payments_30d),2)   AS avg_late_30d
FROM credit_history
GROUP BY 1
ORDER BY MIN(credit_score) DESC;

-- 7.2  Loan approval trends: monthly approval rate over time
SELECT
    DATE_TRUNC('month', application_date)::date       AS month,
    COUNT(*)                                          AS applications,
    SUM(CASE WHEN approval_status='Approved' THEN 1 ELSE 0 END) AS approved,
    ROUND(100.0 * SUM(CASE WHEN approval_status='Approved' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*),0), 1)                    AS approval_rate_pct
FROM loan_applications
GROUP BY 1
ORDER BY 1;

-- 7.3  Customer segmentation: income band x employment, with approval behaviour
SELECT
    c.employment_type,
    CASE
        WHEN c.annual_income >= 1500000 THEN 'High (15L+)'
        WHEN c.annual_income >=  600000 THEN 'Mid (6-15L)'
        ELSE 'Entry (<6L)'
    END                                              AS income_band,
    COUNT(DISTINCT c.customer_id)                    AS customers,
    ROUND(AVG(ch.credit_score),0)                    AS avg_credit_score,
    ROUND(100.0*AVG(CASE WHEN la.approval_status='Approved' THEN 1.0 ELSE 0 END),1) AS approval_rate_pct
FROM customers c
JOIN credit_history ch    ON ch.customer_id = c.customer_id
LEFT JOIN loan_applications la ON la.customer_id = c.customer_id
GROUP BY 1,2
ORDER BY 1,2;

-- 7.4  High-risk customer identification (rule-based watchlist)
SELECT
    c.customer_id, c.first_name, c.last_name, c.city,
    ch.credit_score, ch.credit_utilization_ratio,
    ch.num_late_payments_90d, ch.num_defaults_prior
FROM customers c
JOIN credit_history ch ON ch.customer_id = c.customer_id
WHERE ch.credit_score < 600
   OR ch.credit_utilization_ratio > 0.80
   OR ch.num_defaults_prior >= 1
   OR ch.num_late_payments_90d >= 2
ORDER BY ch.credit_score ASC
LIMIT 100;

-- 7.5  Default rate analysis by loan type (disbursed loans only)
SELECT
    loan_type,
    COUNT(*)                                    AS disbursed_loans,
    SUM(loan_default)                           AS defaults,
    ROUND(100.0*AVG(loan_default),2)            AS default_rate_pct,
    ROUND(AVG(interest_rate),2)                 AS avg_interest_rate
FROM loan_applications
WHERE disbursed_flag = 1 AND loan_default IS NOT NULL
GROUP BY loan_type
ORDER BY default_rate_pct DESC;

-- 7.6  Loan amount distribution by loan type
SELECT
    loan_type,
    COUNT(*)                                        AS applications,
    ROUND(MIN(requested_amount),0)                  AS min_amount,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY requested_amount))::numeric,0) AS median_amount,
    ROUND(AVG(requested_amount),0)                  AS avg_amount,
    ROUND(MAX(requested_amount),0)                  AS max_amount
FROM loan_applications
GROUP BY loan_type
ORDER BY avg_amount DESC;

-- 7.7  Monthly approval statistics with disbursed value
SELECT
    TO_CHAR(application_date,'YYYY-MM')             AS month,
    COUNT(*)                                        AS applications,
    SUM(CASE WHEN approval_status='Approved' THEN 1 ELSE 0 END) AS approved,
    SUM(CASE WHEN approval_status='Rejected' THEN 1 ELSE 0 END) AS rejected,
    ROUND(SUM(approved_amount)/1000000.0,2)         AS disbursed_amount_mn
FROM loan_applications
GROUP BY 1
ORDER BY 1;

-- 7.8  Risk categorisation blending bureau score and utilisation
SELECT
    risk_category, COUNT(*) AS customers,
    ROUND(AVG(credit_score),0) AS avg_score
FROM (
    SELECT customer_id, credit_score,
        CASE
            WHEN credit_score >= 700 AND credit_utilization_ratio < 0.4 THEN 'Low Risk'
            WHEN credit_score >= 620                                     THEN 'Medium Risk'
            ELSE 'High Risk'
        END AS risk_category
    FROM credit_history
) t
GROUP BY risk_category
ORDER BY MIN(credit_score) DESC;

-- 7.9  Transaction behaviour analysis: 6-month cash-flow profile per customer
SELECT
    t.customer_id,
    COUNT(*)                                                   AS txn_count,
    SUM(CASE WHEN transaction_type='Credit' THEN amount ELSE 0 END) AS total_inflow,
    SUM(CASE WHEN transaction_type='Debit'  THEN amount ELSE 0 END) AS total_outflow,
    SUM(CASE WHEN category='EMI' THEN amount ELSE 0 END)       AS emi_outflow,
    ROUND(AVG(balance_after),0)                                AS avg_balance
FROM transactions t
GROUP BY t.customer_id
ORDER BY total_outflow DESC
LIMIT 50;

-- 7.10  Top predictors of loan default: default rate sliced by driver
--        (feeds feature-selection / EDA before modelling)
SELECT 'credit_score<600' AS driver,
       ROUND(100.0*AVG(la.loan_default),2) AS default_rate_pct, COUNT(*) AS n
FROM loan_applications la JOIN credit_history ch USING (customer_id)
WHERE la.loan_default IS NOT NULL AND ch.credit_score < 600
UNION ALL
SELECT 'dti>0.5',
       ROUND(100.0*AVG(loan_default),2), COUNT(*)
FROM loan_applications WHERE loan_default IS NOT NULL AND debt_to_income_ratio > 0.5
UNION ALL
SELECT 'prior_default>=1',
       ROUND(100.0*AVG(la.loan_default),2), COUNT(*)
FROM loan_applications la JOIN credit_history ch USING (customer_id)
WHERE la.loan_default IS NOT NULL AND ch.num_defaults_prior >= 1
UNION ALL
SELECT 'utilization>0.8',
       ROUND(100.0*AVG(la.loan_default),2), COUNT(*)
FROM loan_applications la JOIN credit_history ch USING (customer_id)
WHERE la.loan_default IS NOT NULL AND ch.credit_utilization_ratio > 0.8
ORDER BY default_rate_pct DESC;
