import streamlit as st
import json
import requests
import base64

# === GitHub Repo Config ===
OWNER = "aytid"
REPO = "room"
FILE_PATH = "expenses.json"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# === GitHub API Headers ===
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# === Load Expenses from GitHub ===
@st.cache_data(ttl=10)
def load_expenses():
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    elif r.status_code == 404:
        st.error("❌ File not found. Check if `expenses.json` exists in your repo.")
        st.stop()
    else:
        st.error(f"❌ GitHub API error: {r.status_code} — {r.text}")
        st.stop()


# === Save Expenses to GitHub ===
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

# === Calculate Who Owes Whom ===
def calculate_splits(expenses):
    from collections import defaultdict
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

# === Streamlit UI ===
st.title("🏠 Roommate Expense Tracker")

expenses, sha = load_expenses()

with st.form("expense_form"):
    name = st.text_input("Name")
    amount = st.number_input("Amount Spent (₹)", min_value=0.0, step=1.0)
    reason = st.text_input("Reason")
    submit = st.form_submit_button("➕ Add Expense")
    if submit and name and amount > 0 and reason:
        new_entry = {"name": name, "amount": amount, "reason": reason}
        expenses.append(new_entry)
        save_expenses(expenses, sha)
        st.success("Expense added successfully! Refresh to see the updated list.")

st.subheader("📄 All Expenses")
if expenses:
    for e in expenses:
        st.write(f"➡️ **{e['name']}** spent ₹{e['amount']} for *{e['reason']}*")
else:
    st.info("No expenses recorded yet.")

st.subheader("📊 Split Summary")
for line in calculate_splits(expenses):
    st.write(line)
