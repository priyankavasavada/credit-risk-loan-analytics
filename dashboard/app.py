# credit risk dashboard
# run from the project folder: streamlit run dashboard/app.py
import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Credit Risk Dashboard", layout="wide")

BLUE = "#2a78d6"
STATUS_COLORS = {"Approved": "#2a78d6", "Rejected": "#eb6834", "Under Review": "#1baf7a"}
RISK_COLORS = {"Low Risk": "#0ca30c", "Medium Risk": "#fab219", "High Risk": "#d03b3b"}
RISK_ORDER = ["Low Risk", "Medium Risk", "High Risk"]

st.markdown("""
<style>
.banner {background: linear-gradient(120deg, #0d366b, #2a78d6); color: white;
         padding: 28px 32px; border-radius: 14px; margin-bottom: 18px;}
.banner h1 {color: white; margin: 0; font-size: 2rem;}
.banner p {color: #cde2fb; margin: 6px 0 0 0;}
[data-testid="stVerticalBlockBorderWrapper"] {background: #ffffff; border-radius: 12px;}
[data-testid="stMetric"] {background: #ffffff; border: 1px solid #e1e0d9; border-radius: 12px; padding: 14px 18px;}
</style>
""", unsafe_allow_html=True)


def style(chart, height=280):
    return (chart.properties(height=height, background="#ffffff")
            .configure_axis(gridColor="#e1e0d9", domainColor="#c3c2b7", labelColor="#52514e",
                            titleColor="#52514e", tickColor="#c3c2b7")
            .configure_view(strokeWidth=0)
            .configure_legend(orient="top", labelColor="#52514e", titleColor="#52514e"))


def line_chart(data, y, title, fmt, extra_tooltip=(), y_scale=None):
    # line with a hover rule + tooltip on the nearest month
    hover = alt.selection_point(fields=["month"], nearest=True, on="pointerover", empty=False)
    base = alt.Chart(data).encode(x=alt.X("month:T", title=None))
    y_enc = alt.Y(f"{y}:Q", title=title, axis=alt.Axis(format=fmt.replace(".1", "")),
                  scale=y_scale or alt.Undefined)
    line = base.mark_line(color=BLUE, strokeWidth=2, clip=True).encode(y=y_enc)
    points = base.mark_point(color=BLUE, filled=True, size=70).encode(
        y=y_enc, opacity=alt.condition(hover, alt.value(1), alt.value(0)))
    rule = base.mark_rule(color="#c3c2b7").encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("month:T", title="Month", format="%b %Y"),
                 alt.Tooltip(f"{y}:Q", title=title, format=fmt), *extra_tooltip],
    ).add_params(hover)
    return line + points + rule


@st.cache_data
def load_data():
    engine = create_engine("postgresql+psycopg2:///credit_risk")
    loans = pd.read_sql("""
        SELECT la.*, c.state, c.city, ch.credit_score
        FROM loan_applications la
        JOIN customers c USING (customer_id)
        JOIN credit_history ch USING (customer_id)
    """, engine, parse_dates=["application_date"])
    loans["month"] = loans["application_date"].dt.to_period("M").dt.to_timestamp()

    scored = pd.read_sql("""
        SELECT s.*, c.state, c.city
        FROM scored_customers s
        JOIN customers c USING (customer_id)
    """, engine, parse_dates=["application_date"])

    credit = pd.read_sql("""
        SELECT customer_id, credit_score, credit_utilization_ratio, num_late_payments_30d,
               num_late_payments_90d, num_defaults_prior, bankruptcies, num_open_accounts
        FROM credit_history
    """, engine)
    return loans, scored, credit


loans, scored, credit = load_data()

# ---- filters ----
st.sidebar.header("Filters")
loan_types = st.sidebar.multiselect("Loan type", sorted(loans["loan_type"].unique()))
states = st.sidebar.multiselect("State", sorted(loans["state"].unique()))
risk_cats = st.sidebar.multiselect("Risk category", RISK_ORDER, help="Applies to the risk charts and customer list")
months = sorted(loans["month"].dt.strftime("%Y-%m").unique())
start, end = st.sidebar.select_slider("Application month", options=months, value=(months[0], months[-1]))

df = loans[loans["month"].between(pd.Timestamp(start), pd.Timestamp(end))]
sc = scored[scored["application_date"].dt.strftime("%Y-%m").between(start, end)]
if loan_types:
    df = df[df["loan_type"].isin(loan_types)]
    sc = sc[sc["loan_type"].isin(loan_types)]
if states:
    df = df[df["state"].isin(states)]
    sc = sc[sc["state"].isin(states)]
if risk_cats:
    sc = sc[sc["risk_category"].isin(risk_cats)]

st.markdown("""
<div class="banner">
  <h1>Credit Risk & Loan Approval Dashboard</h1>
  <p>Credora Finance retail lending book · Jul 2022 – Jun 2024</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("No applications match these filters.")
    st.stop()

decided = df[df["approval_status"] != "Under Review"]
disbursed = df[df["loan_default"].notna()]

# ---- KPIs ----
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Applications", f"{len(df):,}")
k2.metric("Approval rate", f"{(decided['approval_status'] == 'Approved').mean():.1%}",
          help="Approved out of decided applications (Under Review left out)")
k3.metric("Default rate", f"{disbursed['loan_default'].mean():.1%}" if len(disbursed) else "-",
          help="Defaulted out of disbursed loans")
k4.metric("Disbursed value", f"₹{disbursed['approved_amount'].sum() / 1e7:,.1f} Cr")
k5.metric("High-risk customers", f"{(sc['risk_category'] == 'High Risk').sum():,}",
          help="Customers whose latest application scored 35 or more")

# tab and customer are kept in the url so a view can be shared as a link
overview, risk_tab, lookup = st.tabs(["Overview", "Portfolio risk", "Customer lookup"], key="tab", bind="query-params")

# ================= OVERVIEW =================
with overview:
    c1, c2 = st.columns(2)

    monthly = decided.groupby("month").agg(
        decided=("application_id", "count"),
        approved=("approval_status", lambda s: (s == "Approved").sum()),
    ).reset_index()
    monthly["approval_rate"] = monthly["approved"] / monthly["decided"]

    with c1.container(border=True):
        st.subheader("Approval rate by month")
        st.altair_chart(style(line_chart(monthly, "approval_rate", "Approval rate", ".1%",
                                         [alt.Tooltip("approved:Q", title="Approved"),
                                          alt.Tooltip("decided:Q", title="Decided")])), width="stretch")

    counts = df.groupby("month").size().reset_index(name="applications")
    with c2.container(border=True):
        st.subheader("Applications per month")
        cols = alt.Chart(counts).mark_bar(color=BLUE, cornerRadiusEnd=4, size=14).encode(
            x=alt.X("month:T", title=None),
            y=alt.Y("applications:Q", title="Applications"),
            tooltip=[alt.Tooltip("month:T", title="Month", format="%b %Y"),
                     alt.Tooltip("applications:Q", title="Applications")],
        )
        st.altair_chart(style(cols), width="stretch")

    status = df.groupby(["month", "approval_status"]).size().reset_index(name="applications")
    with st.container(border=True):
        st.subheader("Approved vs rejected")
        st.caption("Click a status in the legend to highlight it.")
        pick_status = alt.selection_point(fields=["approval_status"], bind="legend")
        stacked = alt.Chart(status).mark_bar(size=18, stroke="#ffffff", strokeWidth=1).encode(
            x=alt.X("month:T", title=None),
            y=alt.Y("applications:Q", title="Applications"),
            color=alt.Color("approval_status:N", title=None,
                            scale=alt.Scale(domain=list(STATUS_COLORS), range=list(STATUS_COLORS.values()))),
            opacity=alt.condition(pick_status, alt.value(1), alt.value(0.2)),
            order=alt.Order("approval_status:N"),
            tooltip=[alt.Tooltip("month:T", title="Month", format="%b %Y"),
                     alt.Tooltip("approval_status:N", title="Status"),
                     alt.Tooltip("applications:Q", title="Applications")],
        ).add_params(pick_status)
        st.altair_chart(style(stacked, 300), width="stretch")
        with st.expander("Show data"):
            table = status.pivot(index="month", columns="approval_status", values="applications").fillna(0).astype(int)
            table.index = table.index.strftime("%Y-%m")
            st.dataframe(table, width="stretch")

    # geography, click a state to see its cities
    with st.container(border=True):
        st.subheader("Loans by state")
        measure = st.radio("Show", ["Applications", "Disbursed value (₹ Cr)", "Approval rate", "Default rate"],
                           horizontal=True, label_visibility="collapsed")

        def geo_table(data, by):
            return data.groupby(by).agg(
                applications=("application_id", "count"),
                disbursed_value=("approved_amount", lambda s: s.sum() / 1e7),
                approval_rate=("approval_status", lambda s: (s[s != "Under Review"] == "Approved").mean()),
                default_rate=("loan_default", "mean"),
            ).reset_index()

        geo = geo_table(df, "state")
        field = {"Applications": "applications", "Disbursed value (₹ Cr)": "disbursed_value",
                 "Approval rate": "approval_rate", "Default rate": "default_rate"}[measure]
        is_rate = "rate" in field

        pick_state = alt.selection_point(fields=["state"], name="pick_state")
        state_bars = alt.Chart(geo).mark_bar(cornerRadiusEnd=4, size=16).encode(
            x=alt.X(f"{field}:Q", title=measure, axis=alt.Axis(format="%" if is_rate else ",.0f")),
            y=alt.Y("state:N", title=None, sort="-x"),
            color=alt.condition(pick_state, alt.value(BLUE), alt.value("#b7d3f6")),
            tooltip=[alt.Tooltip("state:N", title="State"),
                     alt.Tooltip("applications:Q", title="Applications"),
                     alt.Tooltip("disbursed_value:Q", title="Disbursed (₹ Cr)", format=",.1f"),
                     alt.Tooltip("approval_rate:Q", title="Approval rate", format=".1%"),
                     alt.Tooltip("default_rate:Q", title="Default rate", format=".1%")],
        ).add_params(pick_state)
        event = st.altair_chart(style(state_bars, 380), width="stretch", on_select="rerun", key="state_chart")

        picked = [p["state"] for p in event.selection.get("pick_state", [])]
        if picked:
            st.markdown(f"**Cities in {', '.join(picked)}**")
            cities = geo_table(df[df["state"].isin(picked)], "city").sort_values("applications", ascending=False)
            st.dataframe(cities, hide_index=True, width="stretch", column_config={
                "city": "City", "applications": "Applications",
                "disbursed_value": st.column_config.NumberColumn("Disbursed (₹ Cr)", format="%.1f"),
                "approval_rate": st.column_config.NumberColumn("Approval rate", format="percent"),
                "default_rate": st.column_config.NumberColumn("Default rate", format="percent"),
            })
        else:
            st.caption("Click a bar to see the cities in that state.")

# ================= PORTFOLIO RISK =================
with risk_tab:
    c1, c2 = st.columns(2)

    by_type = disbursed.groupby("loan_type").agg(
        loans=("application_id", "count"), defaults=("loan_default", "sum"),
        default_rate=("loan_default", "mean")).reset_index()

    with c1.container(border=True):
        st.subheader("Default rate by loan type")
        pick_type = alt.selection_point(fields=["loan_type"], name="pick_type")
        bars = alt.Chart(by_type).mark_bar(cornerRadiusEnd=4, size=22).encode(
            x=alt.X("default_rate:Q", title="Default rate", axis=alt.Axis(format="%")),
            y=alt.Y("loan_type:N", title=None, sort="-x"),
            color=alt.condition(pick_type, alt.value(BLUE), alt.value("#b7d3f6")),
            tooltip=[alt.Tooltip("loan_type:N", title="Loan type"),
                     alt.Tooltip("default_rate:Q", title="Default rate", format=".1%"),
                     alt.Tooltip("defaults:Q", title="Defaults"),
                     alt.Tooltip("loans:Q", title="Disbursed loans")],
        ).add_params(pick_type)
        event = st.altair_chart(style(bars), width="stretch", on_select="rerun", key="type_chart")
        picked_types = [p["loan_type"] for p in event.selection.get("pick_type", [])]

    with c2.container(border=True):
        trend = disbursed[disbursed["loan_type"].isin(picked_types)] if picked_types else disbursed
        label = ", ".join(picked_types) if picked_types else "all loan types"
        st.subheader("Default rate by quarter")
        st.caption(f"Showing {label}. Click a loan type on the left to change it.")
        q = trend.assign(month=trend["application_date"].dt.to_period("Q").dt.to_timestamp())
        q = q.groupby("month").agg(default_rate=("loan_default", "mean"), loans=("application_id", "count")).reset_index()
        st.altair_chart(style(line_chart(q, "default_rate", "Default rate", ".1%",
                                         [alt.Tooltip("loans:Q", title="Disbursed loans")])), width="stretch")

    c3, c4 = st.columns(2)

    risk = sc["risk_category"].value_counts().reindex(RISK_ORDER, fill_value=0).reset_index()
    risk.columns = ["risk_category", "customers"]
    total = risk["customers"].sum()
    risk["share"] = risk["customers"] / total if total else 0

    with c3.container(border=True):
        st.subheader("Customer risk distribution")
        st.caption("Latest application per customer. Low 0-19, Medium 20-34, High 35-100.")
        seg = alt.Chart(risk).mark_bar(size=56, stroke="#ffffff", strokeWidth=2).encode(
            x=alt.X("customers:Q", stack="normalize", title=None, axis=alt.Axis(format="%")),
            color=alt.Color("risk_category:N", title=None,
                            scale=alt.Scale(domain=RISK_ORDER, range=list(RISK_COLORS.values()))),
            order=alt.Order("order:Q"),
            tooltip=[alt.Tooltip("risk_category:N", title="Category"),
                     alt.Tooltip("customers:Q", title="Customers"),
                     alt.Tooltip("share:Q", title="Share", format=".1%")],
        ).transform_calculate(order=f"indexof({RISK_ORDER}, datum.risk_category)")
        st.altair_chart(style(seg, 110), width="stretch")
        for col, row in zip(st.columns(3), risk.itertuples()):
            col.metric(row.risk_category, f"{row.customers:,}")
            col.caption(f"{row.share:.0%} of customers")

    scores = df.groupby("month")["credit_score"].mean().reset_index()
    with c4.container(border=True):
        st.subheader("Average applicant credit score")
        st.caption("Bureau scores are a single June 2024 snapshot, shown by application month.")
        st.altair_chart(style(line_chart(scores, "credit_score", "Avg credit score", ".0f",
                                         y_scale=alt.Scale(domain=[550, 750]))), width="stretch")

    # watchlist
    with st.container(border=True):
        st.subheader("High-risk customer list")
        f1, f2 = st.columns([1, 2])
        only_active = f1.checkbox("Only approved loans", value=True)
        min_score = f2.slider("Minimum risk score", 0, 100, 0 if risk_cats else 35)

        watch = sc[sc["risk_score"] >= min_score]
        if only_active:
            watch = watch[watch["approval_status"] == "Approved"]
        watch = watch.sort_values("risk_score", ascending=False)
        watch = watch[["customer_id", "city", "state", "loan_type", "approval_status", "risk_score",
                       "risk_category", "default_probability", "top_factors"]]

        st.caption(f"{len(watch):,} customers")
        st.dataframe(watch, hide_index=True, width="stretch", column_config={
            "customer_id": "Customer", "city": "City", "state": "State", "loan_type": "Loan type",
            "approval_status": "Status", "risk_category": "Risk category", "top_factors": "Top risk factors",
            "risk_score": st.column_config.ProgressColumn("Risk score", min_value=0, max_value=100, format="%d"),
            "default_probability": st.column_config.NumberColumn("P(default)", format="%.2f"),
        })
        st.download_button("Download list as CSV", watch.to_csv(index=False), "high_risk_customers.csv")

# ================= CUSTOMER LOOKUP =================
with lookup:
    st.caption("Look up any scored customer to see their risk score and what drives it.")
    cust = st.selectbox("Customer ID", sorted(scored["customer_id"]), index=None, placeholder="Type a customer ID",
                        key="customer", bind="query-params")

    if cust:
        row = scored[scored["customer_id"] == cust].iloc[0]
        bureau = credit[credit["customer_id"] == cust].iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Risk score", int(row["risk_score"]))
        m2.metric("Risk category", row["risk_category"])
        m3.metric("Default probability", f"{row['default_probability']:.1%}")
        m4.metric("Model says", "Default" if row["predicted_default"] else "Repay")

        with st.container(border=True):
            st.markdown(f"**Biggest factors pushing the score up:** {row['top_factors'].replace('_', ' ')}")
            b = st.columns(7)
            b[0].metric("Credit score", int(bureau["credit_score"]))
            b[1].metric("Utilization", f"{bureau['credit_utilization_ratio']:.0%}")
            b[2].metric("Late 30d", int(bureau["num_late_payments_30d"]))
            b[3].metric("Late 90d", int(bureau["num_late_payments_90d"]))
            b[4].metric("Prior defaults", int(bureau["num_defaults_prior"]))
            b[5].metric("Bankruptcies", int(bureau["bankruptcies"]))
            b[6].metric("Accounts", int(bureau["num_open_accounts"]))

        st.markdown(f"**Applications** (score is based on the latest one, {row['application_id']})")
        history = loans[loans["customer_id"] == cust].sort_values("application_date", ascending=False)
        st.dataframe(history[["application_id", "application_date", "loan_type", "requested_amount",
                              "debt_to_income_ratio", "approval_status", "approved_amount", "loan_default"]],
                     hide_index=True, width="stretch", column_config={
                         "application_id": "Application", "loan_type": "Loan type",
                         "application_date": st.column_config.DateColumn("Date"),
                         "requested_amount": st.column_config.NumberColumn("Requested (₹)", format="localized"),
                         "debt_to_income_ratio": st.column_config.NumberColumn("DTI", format="%.2f"),
                         "approval_status": "Status",
                         "approved_amount": st.column_config.NumberColumn("Approved (₹)", format="localized"),
                         "loan_default": st.column_config.NumberColumn("Defaulted", format="%d"),
                     })
