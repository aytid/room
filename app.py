import streamlit as st
import json
import requests
import base64
import pandas as pd
from collections import defaultdict
from datetime import datetime

# === CONFIG ===
OWNER = "aytid"
REPO = "room"
FILE_PATH = "expenses.json"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# === GitHub Load & Save ===
@st.cache_data(ttl=10)
def load_expenses():
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    elif r.status_code == 404:
        return [], None
    else:
        st.error(f"❌ GitHub API error: {r.status_code} — {r.text}")
        st.stop()

def save_expenses(expenses, sha=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"
    encoded = base64.b64encode(json.dumps(expenses, indent=2).encode()).decode()
    payload = {
        "message": "Update expenses via Streamlit",
        "content": encoded,
        "branch": "main",
    }
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=headers, json=payload)
    if res.status_code not in [200, 201]:
        st.error("Error saving expenses to GitHub.")
        st.stop()

# === Split Logic ===
def calculate_splits(expenses):
    totals = defaultdict(float)
    for e in expenses:
        totals[e["name"]] += float(e["amount"])
    people = list(totals.keys())
    avg = sum(totals.values()) / len(people)
    balances = {p: round(totals[p] - avg, 2) for p in people}
    payers = [(p, -amt) for p, amt in balances.items() if amt < 0]
    receivers = [(p, amt) for p, amt in balances.items() if amt > 0]
    i = j = 0
    transactions = []
    while i < len(payers) and j < len(receivers):
        payer, pay_amt = payers[i]
        receiver, recv_amt = receivers[j]
        transfer = min(pay_amt, recv_amt)
        transactions.append(f"💸 {payer} should pay ₹{transfer} to {receiver}")
        pay_amt -= transfer
        recv_amt -= transfer
        if pay_amt == 0: i += 1
        else: payers[i] = (payer, pay_amt)
        if recv_amt == 0: j += 1
        else: receivers[j] = (receiver, recv_amt)
    return transactions

# === App UI ===
st.title("🏠 Roommate Expense Tracker")

expenses, sha = load_expenses()

NAMES = ["Sai varnith", "Pavan", "Aryan", "Sai Deekshith", "Mukhesh Kumar", "Rohan Aditya"]

with st.form("expense_form"):
    name = st.selectbox("Name", NAMES)
    amount = st.number_input("Amount Spent (₹)", min_value=0.0, step=1.0)
    reason = st.text_input("Reason")
    date = st.date_input("Date", value=datetime.today())
    submit = st.form_submit_button("➕ Add Expense")
    if submit and name and amount > 0 and reason:
        new_entry = {"name": name, "amount": amount, "reason": reason, "date": str(date)}
        expenses.append(new_entry)
        save_expenses(expenses, sha)
        st.success("Expense added successfully! Refresh to see updated table.")

# === Filters ===
st.subheader("📄 All Expenses")
filter_name = st.selectbox("Filter by person", ["All"] + NAMES)

filtered = [e for e in expenses if filter_name == "All" or e["name"] == filter_name]

if filtered:
    df = pd.DataFrame(filtered)
    df["amount"] = df["amount"].astype(float)
    df["date"] = pd.to_datetime(df["date"])
    st.dataframe(df.sort_values(by="date", ascending=False))
else:
    st.info("No matching expenses found.")

# === Charts ===
st.subheader("📊 Expense Chart")
chart_df = pd.DataFrame(filtered)
if not chart_df.empty:
    chart_data = chart_df.groupby("name")["amount"].sum().reset_index()
    st.bar_chart(chart_data.set_index("name"))

# === Split View ===
st.subheader("📤 Split Summary")
for line in calculate_splits(expenses):
    st.write(line)
