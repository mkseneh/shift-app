import streamlit as st
from datetime import datetime, timedelta, date
import requests

st.set_page_config(page_title="Shift Cover Calculator", layout="centered")

# =========================
# Fixed staff groups
# =========================
groups = {
    "Group 1": ["KC", "LG"],
    "Group 2": ["AB", "LT"],
    "Group 3": ["FB", "PA"],
    "Group 4": ["Mo", "MS"],
}

all_staff = []
for members in groups.values():
    all_staff.extend(members)

person_to_group = {}
for group_name, members in groups.items():
    for member in members:
        person_to_group[member] = group_name

# =========================
# 8-day repeating cycle
# =========================
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

# =========================
# Real cycle start dates
# =========================
group_cycle_start = {
    "Group 1": "19-03-2026",
    "Group 2": "17-03-2026",
    "Group 3": "21-03-2026",
    "Group 4": "23-03-2026",
}

# Fixed region only
REGION_LABEL = "England and Wales"
REGION_KEY = "england-and-wales"

DAY_SHIFT_TIME = "07:00-19:00"
NIGHT_SHIFT_TIME = "19:00-07:00 next day"

MIN_DATE = datetime.strptime("01-06-2020", "%d-%m-%Y")
BANK_HOLIDAY_URL = "https://www.gov.uk/bank-holidays.json"


@st.cache_data
def load_bank_holidays():
    try:
        response = requests.get(BANK_HOLIDAY_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        parsed = {}
        for region_key, region_data in data.items():
            parsed[region_key] = {}
            for event in region_data.get("events", []):
                event_date = event.get("date", "")
                title = event.get("title", "Bank Holiday")
                notes = event.get("notes", "")
                bunting = event.get("bunting", False)

                parsed[region_key][event_date] = {
                    "title": title,
                    "notes": notes,
                    "bunting": bunting,
                }

        return parsed, None
    except Exception as e:
        return {}, f"Could not load UK bank holidays: {e}"


bank_holiday_data, bank_holiday_error = load_bank_holidays()


def parse_date(date_text: str) -> datetime:
    return datetime.strptime(date_text, "%d-%m-%Y")


def fmt_date(d: datetime) -> str:
    return d.strftime("%d-%m-%Y")


def to_iso_date(date_text: str) -> str:
    return parse_date(date_text).strftime("%Y-%m-%d")


def get_day_name(date_text: str) -> str:
    return parse_date(date_text).strftime("%A")


def get_group_state(group_name: str, date_text: str) -> str:
    d = parse_date(date_text)
    start = parse_date(group_cycle_start[group_name])
    days_diff = (d - start).days
    idx = days_diff % 8
    return cycle[idx]


def get_day_staff(date_text: str) -> list[str]:
    staff = []
    for group_name, members in groups.items():
        if get_group_state(group_name, date_text) == "Day Shift":
            staff.extend(members)
    return staff


def get_night_staff(date_text: str) -> list[str]:
    staff = []
    for group_name, members in groups.items():
        if get_group_state(group_name, date_text) == "Night Shift":
            staff.extend(members)
    return staff


def get_off_staff(date_text: str) -> list[str]:
    day_staff = get_day_staff(date_text)
    night_staff = get_night_staff(date_text)
    return [p for p in all_staff if p not in day_staff and p not in night_staff]


def get_previous_date(date_text: str) -> str:
    return fmt_date(parse_date(date_text) - timedelta(days=1))


def get_next_date(date_text: str) -> str:
    return fmt_date(parse_date(date_text) + timedelta(days=1))


def get_bank_holiday_text(date_text: str) -> str:
    iso_date = to_iso_date(date_text)

    if bank_holiday_error:
        return f"Unable to load ({bank_holiday_error})"

    region_events = bank_holiday_data.get(REGION_KEY, {})
    holiday = region_events.get(iso_date)

    if holiday:
        title = holiday.get("title", "Bank Holiday")
        notes = holiday.get("notes", "").strip()
        if notes:
            return f"{title} - {notes}"
        return title

    return "None"


def get_date_range_for_group(group_name: str, date_text: str):
    current_state = get_group_state(group_name, date_text)
    current_date = parse_date(date_text)

    start_date = current_date
    while True:
        prev_date = start_date - timedelta(days=1)
        prev_text = fmt_date(prev_date)
        if get_group_state(group_name, prev_text) != current_state:
            break
        start_date = prev_date

    end_date = current_date
    while True:
        next_date = end_date + timedelta(days=1)
        next_text = fmt_date(next_date)
        if get_group_state(group_name, next_text) != current_state:
            break
        end_date = next_date

    return fmt_date(start_date), fmt_date(end_date), current_state


def get_selected_staff_status_with_range(person: str, date_text: str):
    group_name = person_to_group[person]
    start_date, end_date, state = get_date_range_for_group(group_name, date_text)

    if state == "Day Shift":
        label = f"Working Day Shift ({DAY_SHIFT_TIME})"
    elif state == "Night Shift":
        label = f"Working Night Shift ({NIGHT_SHIFT_TIME})"
    else:
        label = "Time Off"

    return label, start_date, end_date


def build_cover_info(person: str, date_text: str):
    day_staff = get_day_staff(date_text)
    night_staff = get_night_staff(date_text)

    prev_date = get_previous_date(date_text)
    next_date = get_next_date(date_text)

    prev_night_staff = get_night_staff(prev_date)
    next_day_staff = get_day_staff(next_date)

    if person in day_staff:
        valid_covers = []
        for candidate in all_staff:
            if candidate == person:
                continue
            if candidate in day_staff:
                continue
            if candidate in night_staff:
                continue
            if candidate in prev_night_staff:
                continue
            valid_covers.append(candidate)

        return {
            "status_type": "day",
            "leave_approval": "YES" if valid_covers else "NO",
            "possible_cover": valid_covers,
        }

    if person in night_staff:
        valid_covers = []
        for candidate in all_staff:
            if candidate == person:
                continue
            if candidate in day_staff:
                continue
            if candidate in night_staff:
                continue
            if candidate in next_day_staff:
                continue
            valid_covers.append(candidate)

        return {
            "status_type": "night",
            "leave_approval": "YES" if valid_covers else "NO",
            "possible_cover": valid_covers,
        }

    return {
        "status_type": "off",
        "leave_approval": "Not needed",
        "possible_cover": [],
    }


# =========================
# UI
# =========================
st.title("Shift Cover Calculator")

today = date.today()
min_date_only = MIN_DATE.date()
default_date = today if today >= min_date_only else min_date_only

selected_date = st.date_input(
    "Select date",
    value=default_date,
    min_value=min_date_only,
    format="DD/MM/YYYY",
)

date_text = selected_date.strftime("%d-%m-%Y")
day_name = get_day_name(date_text)

default_staff_index = all_staff.index("Mo") if "Mo" in all_staff else 0
person = st.selectbox("Select staff", all_staff, index=default_staff_index)

selected_datetime = parse_date(date_text)
if selected_datetime < MIN_DATE:
    st.error("Date is before 01-06-2020")
    st.stop()

day_staff = get_day_staff(date_text)
night_staff = get_night_staff(date_text)
off_staff = get_off_staff(date_text)
holiday_text = get_bank_holiday_text(date_text)

selected_status, selected_from, selected_to = get_selected_staff_status_with_range(person, date_text)
cover_info = build_cover_info(person, date_text)

st.markdown("### Summary")
st.markdown(f"**Date:** {date_text} ({day_name})")
st.markdown(f"**UK Bank Holiday ({REGION_LABEL}):** {holiday_text}")

st.divider()

st.markdown("### Shift Cover")
st.markdown(f"**Day Shift ({DAY_SHIFT_TIME}):** {', '.join(day_staff) if day_staff else 'None'}")
st.markdown(f"**Night Shift ({NIGHT_SHIFT_TIME}):** {', '.join(night_staff) if night_staff else 'None'}")
st.markdown(f"**Time Off:** {', '.join(off_staff) if off_staff else 'None'}")

st.divider()

st.markdown("### Selected Staff")
st.markdown(f"**Name:** {person}")
st.markdown(f"**Status:** {selected_status} ({selected_from} to {selected_to})")
st.markdown(f"**Leave Approval:** {cover_info['leave_approval']}")

if cover_info["status_type"] == "off":
    st.markdown(f"**Reason:** {person} is already on Time Off ({selected_from} to {selected_to})")
else:
    possible_cover_text = ", ".join(cover_info["possible_cover"]) if cover_info["possible_cover"] else "None"
    st.markdown(f"**Possible Cover:** {possible_cover_text}")