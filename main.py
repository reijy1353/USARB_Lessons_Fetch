import os
import json
from re import S
from typing import Any, Literal, Tuple, overload
from dotenv import load_dotenv
from datetime import datetime, date, time, timedelta, timezone
import caldav
from caldav.davclient import get_davclient
from caldav.lib.error import NotFoundError

from data_parser import get_raw_schedule_data, get_lesson_id


# Load .env
load_dotenv()

# Get the variables/contanst from the .env file
CALDAV_URL=os.getenv("CALDAV_URL")
ICLOUD_USERNAME=os.getenv("ICLOUD_USERNAME")
ICLOUD_PASSWORD=os.getenv("ICLOUD_PASSWORD")
CALENDAR_NAME=os.getenv("CALENDAR_NAME")
GROUP_NAME=os.getenv("GROUP_NAME")

# Other constants
FIRST_DAY = date(2025, 9, 1)
FIRST_LESSON_TIME = time(8, 0)


class CalendarSchedule:
    def __init__(self) -> None:
        "Setting up the environmental variables"
        self.caldav_url = CALDAV_URL
        self.username = ICLOUD_USERNAME
        self.password = ICLOUD_PASSWORD
        self.calendar_name = CALENDAR_NAME
        self.group_name = GROUP_NAME
        self.debug: str = False
        
    def connect(self) -> caldav.Principal:
        """Connecting to the calendar
        
        Returns:
            my_principal: Your principal
        """
        with get_davclient(
            username=self.username,
            password=self.password,
            url=self.caldav_url,
        ) as client:
            # Try/Except block for receiving my_principal from calDAV
            try:
                my_principal = client.principal()
            except Exception as e:
                print(f"There's a problem making a connection: {e}")
            finally:
                # Debug
                if self.debug:
                    print(f"\n\nDEBUG: type {type(my_principal)}")
                    print(f"\n\nDEBUG: my_principal: {my_principal}")
                
                # Returning client.principal() if everything's fine
                return my_principal
            
    def _get_lesson_time(self, lesson_nr: int):
        """Get lesson start and end time by lesson_nr"""
        # Coming a date with first lesson's start time
        dt = datetime.combine(datetime.today(), FIRST_LESSON_TIME)

        # Get lesson_start_time
        lesson_start_time = dt + (lesson_nr - 1) * timedelta(hours=1, minutes=45)

        # Get lesson_end_time
        lesson_end_time = lesson_start_time + timedelta(hours=1, minutes=30)
            
        if self.debug:
            print(f"\n\nDEBUG: st = {lesson_start_time.time()}, et = {lesson_end_time.time()}")
        
        return lesson_start_time.time(), lesson_end_time.time()

    def _get_this_week(self) -> int:
        """Get lesson week from today"""
        # Get today's date
        today = datetime.today().date()

        # Get the day difference
        days_difference = (today - FIRST_DAY).days
        
        # Calculate week number
        week_number = (days_difference // 7) + 1

        # Debug
        if self.debug:
            print(f"DEBUG: week_number: {week_number}")

        return week_number

    @overload
    def _get_date_from_this_week_on(
        self,
        week: int | None = ...,
        postpone: int = ...,
        mode: Literal["dates"] = ...,
    ) -> tuple[date, date]: ...

    @overload
    def _get_date_from_this_week_on(
        self,
        week: int | None = ...,
        postpone: int = ...,
        mode: Literal["weeks"] = ...,
    ) -> list[int]: ...

    def _get_date_from_this_week_on(self, week: int | None = None, postpone: int = 3, mode: str = "dates"):
        """Get a range of dates, from first day of the university week, to the 
        one calculated by formula week + postpone (e.g. week = 10, postone = 3)
        returns the range from start of week 10, till then end of week 10 + 3 = 13.

        Args:
            week (int): A week (1-the_end). Defaults to self.get_this_week()
            postpone (int): How many weeks on you want to prolong your calendar. Defaults to 3.

        Returns:
            mode ("dates"): a range of dates from the first day of `week` to the last day of `week + postpone`, OR
            mode ("weeks"): a range of week numbers (week, week + postpone)
        """
        # If no week is given, use "this" week by default
        if week is None:
            week = self._get_this_week()
            print(f"week wasn't given, setting up the week your in by default (week = {week})")

        # for mode = "weeks" return the range of weeks
        if mode == "weeks":
            # Debug
            if self.debug:
                print(f"\n\nDEBUG: mode \"weeks\" active returns {list[int](range(week, week + postpone))}")
            
            return list[int](range(week, week + postpone))

        # Get the start_date
        # formula: start_date = FIRST_DAY + 7 * week
        start_date = FIRST_DAY + timedelta(days=7) * (week - 1)

        # Get the end_date
        # forumula: end_date = (start_date + 7 * postpone) - 1
        end_date = (start_date + timedelta(days=7) * postpone) - timedelta(days=1)

        # Debug
        if self.debug:
            print(f"\n\nDEBUG: mode \"dates\" active:")
            print(f"DEBUG: start_date = {start_date}")
            print(f"DEBUG: end_date = {end_date}")
        
        # Return (types vary by mode)
        if mode == "dates":
            return start_date, end_date
        else:
            raise ValueError("mode must be either 'dates' or 'weeks'")
            
    def _get_lesson_date_and_time(self, week: int = 1, day: int = 1, lesson_nr: int = 1) -> Tuple[datetime, datetime]:
        """Return start and end date & time of a specific lesson

        Args:
            week (int, optional): the week (1-20). Defaults to 1.
            lesson_nr (int, optional): the lesson nr (1-8). Defaults to 1.

        Returns:
            datetime: the date and the time of a specific lesson
        """

        # Get the date of the lesson using week and day
        dt = (FIRST_DAY + timedelta(days=7) * (week - 1)) + timedelta(days=day-1)
        
        # Get the time of the lesson using _get_lesson_time method
        lt_start, lt_end = self._get_lesson_time(lesson_nr=lesson_nr)
        
        # Combine date with lessons start and end time
        dt_start = datetime.combine(dt, lt_start)
        dt_end = datetime.combine(dt, lt_end)

        # Convert to utc
        dt_start = dt_start.astimezone(timezone.utc)
        dt_end = dt_end.astimezone(timezone.utc)

        return dt_start, dt_end

    def _stringify_ics_datetime(self, dt: datetime | None = None) -> str:
        "Return a proper ics datetime string"
        return dt.strftime("%Y%m%dT%H%M%SZ")

    def _convert_to_ics_datetime(self, dt_start: datetime = None, dt_end: datetime = None) -> Tuple[str, str]:
        "Returns dt start and end formated by .ics data requirements"
        dt_start = self._stringify_ics_datetime(dt_start)
        dt_end = self._stringify_ics_datetime(dt_end)
        return dt_start, dt_end

    def _escape_ical_value(self, value: str) -> str:
        """Escape special characters in iCal values."""
        # Replace newlines with \n
        value = value.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
        # Escape special characters
        value = value.replace('\\', '\\\\')
        value = value.replace(',', '\\,')
        value = value.replace(';', '\\;')
        # Replace newlines in multi-line values with proper formatting
        value = value.replace('\n', '\\n')
        return value
    
    # Feature in later update
    # e.g. where we need to make a difference between two scheules
    def get_data_from_snapshot(self, snapshot_directory: str = "schedule_snapshot.json"):
        """Fetching the data from the last schedule snapshot"""
        # Open the json file and load the snapshot into a variable
        try:
            with open(snapshot_directory, "r") as fp:
                schedule_snapshot = json.load(fp)
        except FileNotFoundError:
            print(f"The file \"{snapshot_directory}\" doesn't exist.")
            return None

        # Debug
        if self.debug:
            print(f"\n\nDEBUG: data from json: {schedule_snapshot}")
        
        return schedule_snapshot
    
    def get_or_create_calendar(self) -> caldav.Calendar:
        """Get the calendar used for schedule, if none exists, it'll create a new one
        naming it by calendar_name from .env

        Returns:
            my_calendar: Your calendar
        """
        # Get my_principal (connect)
        my_principal = self.connect()

        # Try to fetch schedule targeted calendar
        try:
            my_calendar = my_principal.calendar(name=self.calendar_name)
        except NotFoundError:
            print(f"You don't seem to have a calendar named {self.calendar_name}")
            print(f"But we'll create one just for you.")
            my_calendar = my_principal.make_calendar(name=self.calendar_name)
            
        # Debug
        if self.debug:
            print(f"\n\nDEBUG: type {type(my_calendar)}")
            print(f"DEBUG: calendar {my_calendar}")
    
        return my_calendar

    def parse_schedule_data(self, group_name: str = None, weeks: list[int] = None):
        """Pasing the data from get_schedule(), adding it up to a ics data set and
        add to the calendar itself.
        """
        
        # If no group_name provided, get it from .env
        if group_name is None:
            group_name = self.group_name

        # If no weeks provided, get this week and the next 2
        if weeks is None:
            weeks = self._get_date_from_this_week_on(postpone=3, mode="weeks",)

            # Debug
            if self.debug:
                print(f"\n\nDEBUG: The weeks by default are: {weeks}")

        # If we get just one week and it's int transform it into an itreable object
        if isinstance(weeks, int):
            weeks = [weeks]
        
        # Define .ics code for the schedule calendar
        event_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PROID:-//USARB Schedule//EN",
        ]
        
        # The end lines for ics content
        event_lines_end = [
            f"END:VCALENDAR",
            "", 
        ]
        
        # Loop for parsing my_schedule week by week
        for week in weeks:
            my_schedule = get_raw_schedule_data(your_group_name=group_name, university_week=week)
            
            # Loop for parsing every leeson from a university week
            for lesson in my_schedule["week"]:
                # Get the data needed from my_schedule dict
                lesson_nr = lesson["cours_nr"]
                lesson_name = lesson["cours_name"]
                lesson_type = lesson["cours_type"]
                lesson_day = lesson["day_number"]
                office = lesson["cours_office"]
                teacher = lesson["teacher_name"]

                # Get lesson's hash (UID)
                lesson_id = get_lesson_id(lesson_day, lesson_nr, lesson_name, lesson_type,
                                          office, teacher)
                
                # Get dt_start and dt_end, then convert into a proper form
                dt_start, dt_end = self._get_lesson_date_and_time(week, lesson_day, lesson_nr)
                dt_start, dt_end = self._convert_to_ics_datetime(dt_start, dt_end)

                # Generate a summary
                summary = f"{lesson_name} | {lesson_type}"
                _safe_summary = self._escape_ical_value(summary)
                
                # Generate a description
                description_lines = [
                    f"Lesson {lesson_nr}",
                    f"Type: {lesson_type}",
                    f"Office: {office if office else "Unknown"}",
                    f"Teacher: {teacher}"
                ]
                _safe_description = self._escape_ical_value("\n".join(description_lines))

                # Generate ics data
                lesson_lines = [
                    "BEGIN:VEVENT",
                    f"UID:{lesson_id}@usarb-schedule.local",
                    f"DTSTART:{dt_start}",
                    f"DTEND:{dt_end}",
                    f"SUMMARY:{_safe_summary}",
                    f"DESCRIPTION:{_safe_description}",
                    f"LOCATION:{office if office else "Unknown"}",
                    f"OBJECT_ID:{lesson_id}.ics",
                    f"END:VEVENT",
                ]
                
                # Add event/lesson to the ics data
                event_lines.extend(lesson_lines)

                # Debug
                if self.debug:
                    print(f"\n\nDEBUG: ICS Event Lines: {event_lines}")
            
        # Add the end lines to the ics content
        event_lines.extend(event_lines_end)

        # Debug
        if self.debug:
            print(f"\n\nDEBUG: ICS Event Lines (end): {event_lines}")
        
        # Get the properly formatted ics content
        content = "\r\n".join(event_lines)

        # Get the calendar and save the event/events
        my_calendar = self.get_or_create_calendar()
        saved_event = my_calendar.save_event(content.encode("utf-8"))

        # Debug
        if self.debug:
            print(f"DEBUG: Saved event data: {saved_event}")
        
    # This function won't be used in the main process, but it's here for testing purposes
    def fetch_events(self, my_calendar: caldav.Calendar | None = None) -> list[caldav.Event]:
        """Fetching the events from the calendar
        
        Returns:
            my_events: Your events
        """
        # Get the default my_calendar if None
        if my_calendar is None:
            my_calendar = self.get_or_create_calendar()
            
        # Get start and end date (for searching events)
        start_date, end_date = self._get_date_from_this_week_on()

        # Search for events
        my_events = my_calendar.search(
            event=True,
            start=start_date,
            end=end_date,
            expand=True
        )

        # Debug
        if self.debug:
            print(f"\n\nDEBUG: my_events: {my_events}")

        return my_events


# Local testing
if __name__ == "__main__":
    app = CalendarSchedule()
    app.debug = True

    # app.get_date_from_this_week_on(mode="dates")
    # app.get_or_create_calendar()
    # my_events = app.fetch_events()
    # print(my_events[0].data)
    
    # my_calendar = app.get_or_create_calendar()
    # print(my_calendar)

    # my_principal = app.connect()
    # print(my_principal)
    
    # print(datetime.now(timezone.utc))
    
    # app.parse_data_and_save_to_calendar()
    
    # print(app._get_lesson_date_and_time(10, 1, 2))

    app.parse_schedule_data()