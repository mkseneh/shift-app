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
        return f"UK Bank Holiday: Unable to load ({bank_holiday_error})"

    region_events = bank_holiday_data.get(REGION_KEY, {})
    holiday = region_events.get(iso_date)

    if holiday:
        title = holiday.get("title", "Bank Holiday")
        notes = holiday.get("notes", "").strip()
        if notes:
            return f"UK Bank Holiday ({REGION_LABEL}): {title} - {notes}"
        return f"UK Bank Holiday ({REGION_LABEL}): {title}"

    return f"UK Bank Holiday ({REGION_LABEL}): None"


def build_output(date_text: str, person: str) -> str:
    day_name = get_day_name(date_text)
    d = parse_date(date_text)

    if d < MIN_DATE:
        return "Date is before 01-06-2020"

    day_staff = get_day_staff(date_text)
    night_staff = get_night_staff(date_text)
    off_staff = get_off_staff(date_text)

    prev_date = get_previous_date(date_text)
    next_date = get_next_date(date_text)

    prev_night_staff = get_night_staff(prev_date)
    next_day_staff = get_day_staff(next_date)

    holiday_line = get_bank_holiday_text(date_text)

    top_block = (
        f"Date: {date_text} ({day_name})\n"
        f"{holiday_line}\n\n"
        f"Day Shift: {', '.join(day_staff) if day_staff else 'None'}\n"
        f"Night Shift: {', '.join(night_staff) if night_staff else 'None'}\n"
        f"Time Off: {', '.join(off_staff) if off_staff else 'None'}\n\n"
    )

    if person in day_staff:
        shift_type = "Day Shift"
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

        if valid_covers:
            person_block = (
                f"Selected Staff: {person}\n"
                f"Status: Working {shift_type}\n"
                f"Leave Approval: YES\n"
                f"Possible Cover: {', '.join(valid_covers)}"
            )
        else:
            person_block = (
                f"Selected Staff: {person}\n"
                f"Status: Working {shift_type}\n"
                f"Leave Approval: NO\n"
                f"Possible Cover: None"
            )

    elif person in night_staff:
        shift_type = "Night Shift"
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

        if valid_covers:
            person_block = (
                f"Selected Staff: {person}\n"
                f"Status: Working {shift_type}\n"
                f"Leave Approval: YES\n"
                f"Possible Cover: {', '.join(valid_covers)}"
            )
        else:
            person_block = (
                f"Selected Staff: {person}\n"
                f"Status: Working {shift_type}\n"
                f"Leave Approval: NO\n"
                f"Possible Cover: None"
            )

    else:
        person_block = (
            f"Selected Staff: {person}\n"
            f"Status: Time Off\n"
            f"Leave Approval: Not needed\n"
            f"Reason: {person} is already on Time Off"
        )

    return top_block + person_block


# =========================
# UI
# =========================
st.title("Shift Cover Calculator")

today = date.today()
min_date_only = MIN_DATE.date()
default_date = today if today >= min_date_only else min_date_only

st.subheader("Select date")

selected_date = st.date_input(
    "Select date",
    value=default_date,
    min_value=min_date_only,
    format="DD/MM/YYYY",
)

date_text = selected_date.strftime("%d-%m-%Y")

# Default person = Mo
default_staff_index = all_staff.index("Mo") if "Mo" in all_staff else 0
person = st.selectbox("Select staff", all_staff, index=default_staff_index)

output = build_output(date_text, person)

st.divider()
st.text(output)