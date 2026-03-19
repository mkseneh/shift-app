import streamlit as st
from datetime import datetime, timedelta
import requests

# =========================
# DATA (UNCHANGED)
# =========================
groups = {
    "Group 1": ["Karl", "Lax G"],
    "Group 2": ["Tony", "Lax T"],
    "Group 3": ["Frank", "Prakash"],
    "Group 4": ["Mo", "Michal"],
}

all_staff = []
for members in groups.values():
    all_staff.extend(members)

cycle = [
    "Day Shift",
    "Day Shift",
    "Night Shift",
    "Night Shift",
    "Time Off",
    "Time Off",
    "Time Off",
    "Time Off",
]

group_cycle_start = {
    "Group 1": "19-03-2026",
    "Group 2": "17-03-2026",
    "Group 3": "21-03-2026",
    "Group 4": "23-03-2026",
}

holiday_regions = {
    "England and Wales": "england-and-wales",
    "Scotland": "scotland",
    "Northern Ireland": "northern-ireland",
}

MIN_DATE = datetime.strptime("01-06-2020", "%d-%m-%Y")
BANK_HOLIDAY_URL = "https://www.gov.uk/bank-holidays.json"

# =========================
# LOGIC (UNCHANGED)
# =========================
@st.cache_data
def load_bank_holidays():
    try:
        response = requests.get(BANK_HOLIDAY_URL, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except Exception as e:
        return {}, str(e)

bank_data, bank_error = load_bank_holidays()

def parse_date(date_text):
    return datetime.strptime(date_text, "%d-%m-%Y")

def fmt_date(d):
    return d.strftime("%d-%m-%Y")

def get_day_name(date_text):
    return parse_date(date_text).strftime("%A")

def get_group_state(group_name, date_text):
    d = parse_date(date_text)
    start = parse_date(group_cycle_start[group_name])
    return cycle[(d - start).days % 8]

def get_day_staff(date_text):
    return [
        p for g, members in groups.items()
        if get_group_state(g, date_text) == "Day Shift"
        for p in members
    ]

def get_night_staff(date_text):
    return [
        p for g, members in groups.items()
        if get_group_state(g, date_text) == "Night Shift"
        for p in members
    ]

def get_off_staff(date_text):
    day = get_day_staff(date_text)
    night = get_night_staff(date_text)
    return [p for p in all_staff if p not in day and p not in night]

def get_prev_date(date_text):
    return fmt_date(parse_date(date_text) - timedelta(days=1))

def get_next_date(date_text):
    return fmt_date(parse_date(date_text) + timedelta(days=1))

# =========================
# STREAMLIT UI
# =========================
st.title("Senez Shift Cover Calculator")

selected_date = st.date_input("Select date")
date_text = selected_date.strftime("%d-%m-%Y")

person = st.selectbox("Select staff", all_staff)
region_label = st.selectbox("Region", list(holiday_regions.keys()))

# =========================
# OUTPUT
# =========================
day_staff = get_day_staff(date_text)
night_staff = get_night_staff(date_text)
off_staff = get_off_staff(date_text)

prev_night = get_night_staff(get_prev_date(date_text))
next_day = get_day_staff(get_next_date(date_text))

st.markdown(f"**Date:** {date_text} ({get_day_name(date_text)})")

st.markdown(f"**Day Shift:** {', '.join(day_staff)}")
st.markdown(f"**Night Shift:** {', '.join(night_staff)}")
st.markdown(f"**Time Off:** {', '.join(off_staff)}")

# =========================
# PERSON LOGIC (UNCHANGED)
# =========================
if person in day_staff:
    valid = [
        c for c in all_staff
        if c != person
        and c not in day_staff
        and c not in night_staff
        and c not in prev_night
    ]
    st.markdown(f"### {person}")
    st.write("Status: Day Shift")
    st.write("Leave Approval:", "YES" if valid else "NO")
    st.write("Cover:", ", ".join(valid) if valid else "None")

elif person in night_staff:
    valid = [
        c for c in all_staff
        if c != person
        and c not in day_staff
        and c not in night_staff
        and c not in next_day
    ]
    st.markdown(f"### {person}")
    st.write("Status: Night Shift")
    st.write("Leave Approval:", "YES" if valid else "NO")
    st.write("Cover:", ", ".join(valid) if valid else "None")

else:
    st.markdown(f"### {person}")
    st.write("Status: Time Off")
    st.write("Leave Approval: Not needed")