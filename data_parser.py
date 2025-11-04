from datetime import datetime, date
from typing import Dict, List, Optional
from raw_schedule_data_fetch import get_raw_schedule_json


# First week date
WEEK_ZERO_START = date(2025, 9, 1)


# Parsing the date
def _parse_date_str(date_str: str) -> date:
    return datetime.strptime(date_str, "%d.%m.%Y").date()


# Calculating the week properly
def calc_university_week_from_date(target_date: date) -> int:
    delta_days = (target_date - WEEK_ZERO_START).days
    week_index = (delta_days // 7) + 1
    return max(1, week_index)


# Mapping weekday names
def _weekday_name(day_number: int) -> str:
    mapping = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday",
    }
    return mapping.get(day_number, f"Day {day_number}")


# Calculate lesson time window based on lesson number
def _lesson_time_range(lesson_number: int) -> str:
    # Start at 08:00
    start_minutes_total = 8 * 60
    # Each block is 90 min lesson + 15 min break between lessons => 105 min step
    step = 105
    # Compute start for this lesson (1-indexed)
    lesson_start = start_minutes_total + (lesson_number - 1) * step
    lesson_end = lesson_start + 90
    sh, sm = divmod(lesson_start, 60)
    eh, em = divmod(lesson_end, 60)
    return f"{sh:02d}:{sm:02d} - {eh:02d}:{em:02d}"


# Formatting schedule by specific criteria
def format_schedule(grouped: Dict[int, List[dict]]) -> str:
    lines: List[str] = []
    lines.append("Day of the week:")
    for day_number in sorted(grouped.keys()):
        day_lessons = sorted(grouped[day_number], key=lambda l: (l.get("cours_nr") or 0))
        lines.append("")
        lines.append(f"{_weekday_name(day_number)}:")
        for lesson in day_lessons:
            nr = lesson.get("cours_nr")
            name = lesson.get("cours_name") or ""
            ctype = lesson.get("cours_type") or ""
            office = lesson.get("cours_office") or ""
            teacher = lesson.get("teacher_name") or ""
            time_range = _lesson_time_range(nr) if isinstance(nr, int) else ""
            if time_range:
                lines.append(f"Lesson {nr} ({time_range}): {name} {ctype} {office} {teacher}")
            else:
                lines.append(f"Lesson {nr}: {name} {ctype} {office} {teacher}")
    return "\n".join(lines)


# Main function
def parse_raw_schedule_json(
    group_name: str,
    week: Optional[int] = None,
    date_str: Optional[str] = None,
    debug: bool = False,
) -> str:
    if date_str:
        target = _parse_date_str(date_str)
        week = calc_university_week_from_date(target)
    if week is None:
        week = 1

    raw = get_raw_schedule_json(group_name, university_week=week, debug=debug)

    entries = raw.get("week") or []
    grouped: Dict[int, List[dict]] = {}
    for item in entries:
        day_num = item.get("day_number") or 0
        if day_num not in grouped:
            grouped[day_num] = []
        grouped[day_num].append(item)

    output = format_schedule(grouped)
    if debug:
        pass
        # print(output)
    return output


# Local test
if __name__ == "__main__":
    try:
        today_str = datetime.today().strftime("%d.%m.%Y")
        prompt = (
            f"Enter date (dd.mm.yyyy), type 'today' for {today_str}, or leave empty to use week=1: "
        )
        user_date = input(prompt).strip()
    except EOFError:
        user_date = ""
    if user_date:
        if user_date.lower() == "today":
            user_date = today_str
        print(parse_raw_schedule_json("IT11Z", date_str=user_date, debug=True))
    else:
        print(parse_raw_schedule_json("IT11Z", week=1, debug=True))