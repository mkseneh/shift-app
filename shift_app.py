import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
from datetime import datetime, timedelta
import requests

# =========================
# Fixed staff groups
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
# These are the first DAY-DAY dates for each group
# =========================
group_cycle_start = {
    "Group 1": "19-03-2026",
    "Group 2": "17-03-2026",
    "Group 3": "21-03-2026",
    "Group 4": "23-03-2026",
}

# =========================
# Holiday regions
# =========================
holiday_regions = {
    "England and Wales": "england-and-wales",
    "Scotland": "scotland",
    "Northern Ireland": "northern-ireland",
}

MIN_DATE = datetime.strptime("01-06-2020", "%d-%m-%Y")
BANK_HOLIDAY_URL = "https://www.gov.uk/bank-holidays.json"
bank_holiday_data = {}
bank_holiday_error = None


def load_bank_holidays():
    global bank_holiday_data, bank_holiday_error

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

        bank_holiday_data = parsed
        bank_holiday_error = None

    except Exception as e:
        bank_holiday_data = {}
        bank_holiday_error = f"Could not load UK bank holidays: {e}"


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
    region_label = region_var.get()
    region_key = holiday_regions.get(region_label, "england-and-wales")
    iso_date = to_iso_date(date_text)

    if bank_holiday_error:
        return f"UK Bank Holiday: Unable to load ({bank_holiday_error})"

    region_events = bank_holiday_data.get(region_key, {})
    holiday = region_events.get(iso_date)

    if holiday:
        title = holiday.get("title", "Bank Holiday")
        notes = holiday.get("notes", "").strip()
        if notes:
            return f"UK Bank Holiday ({region_label}): {title} - {notes}"
        return f"UK Bank Holiday ({region_label}): {title}"

    return f"UK Bank Holiday ({region_label}): None"


def build_output() -> str:
    date_text = cal.get_date()
    person = staff_var.get()
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


def refresh_display(event=None):
    result.config(text=build_output())


load_bank_holidays()

root = tk.Tk()
root.title("Shift Calculator")
root.geometry("780x820")

tk.Label(root, text="Select a date:", font=("Arial", 11)).pack(pady=5)

today = datetime.today()
start_date = today if today >= MIN_DATE else MIN_DATE

cal = Calendar(
    root,
    date_pattern="dd-mm-yyyy",
    year=start_date.year,
    month=start_date.month,
    day=start_date.day,
)
cal.pack(pady=5)

tk.Label(root, text="Select staff:", font=("Arial", 11)).pack(pady=5)
staff_var = tk.StringVar(value=all_staff[0])
staff_menu = tk.OptionMenu(root, staff_var, *all_staff, command=lambda _: refresh_display())
staff_menu.pack(pady=5)

tk.Label(root, text="UK bank holiday region:", font=("Arial", 11)).pack(pady=5)
region_var = tk.StringVar(value="England and Wales")
region_menu = tk.OptionMenu(
    root,
    region_var,
    *holiday_regions.keys(),
    command=lambda _: refresh_display()
)
region_menu.pack(pady=5)

result = tk.Label(root, text="", font=("Arial", 11), justify="left", anchor="w")
result.pack(pady=15)

cal.bind("<<CalendarSelected>>", refresh_display)

refresh_display()

root.mainloop()