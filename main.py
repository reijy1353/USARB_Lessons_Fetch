import os
import json
from re import S
from typing import Any, Literal, overload
from dotenv import load_dotenv
from datetime import datetime, date, time, timedelta
import caldav
from caldav.davclient import get_davclient
from caldav.lib.error import NotFoundError

from data_parser import save_schedule_to_json

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
        self.caldav_url = CALDAV_URL
        self.username = ICLOUD_USERNAME
        self.password = ICLOUD_PASSWORD
        self.calendar_name = CALENDAR_NAME
        self.group = GROUP_NAME
        self.debug: str = False
        
    def get_lesson_time(self, lesson_nr: int):
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

    def get_this_week(self) -> int:
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
    def get_date_from_this_week_on(
        self,
        week: int | None = ...,
        postpone: int = ...,
        mode: Literal["dates"] = ...,
    ) -> tuple[date, date]: ...

    @overload
    def get_date_from_this_week_on(
        self,
        week: int | None = ...,
        postpone: int = ...,
        mode: Literal["weeks"] = ...,
    ) -> list[int]: ...

    def get_date_from_this_week_on(self, week: int | None = None, postpone: int = 3, mode: str = "dates"):
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
            week = self.get_this_week()
            print(f"week var wasn't given, setting up this week by default (week = {week})")

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
            
        ## TEST: create/save an event

        # Method 1: using .save_event() function
        # november_18 = my_calendar.save_event(
        #     dtstart=datetime(2025, 11, 18, 10),
        #     dtend=datetime(2025, 11, 18, 11),
        #     uid="november-18th",
        #     summary="Here it is\nOr not?",
        # )

        # Method 2: using .save_even() fucntion with icalendar code
        event_code = f"""   BEGIN:VCALENDAR
                            VERSION:2.0
                            PRODID:-//Example Corp.//CalDAV Client//EN
                            BEGIN:VEVENT
                            UID:20200516T060000Z-123401@example.com
                            DTSTAMP:20200516T060000Z
                            DTSTART:20200517T060000Z
                            DTEND:20200517T230000Z
                            RRULE:FREQ=YEARLY
                            SUMMARY:Do the needful
                            END:VEVENT
                            END:VCALENDAR
                            """
            
        # Debug
        if self.debug:
            print(f"\n\nDEBUG: type {type(my_calendar)}")
            print(f"DEBUG: calendar {my_calendar}")
    
        return my_calendar
    
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
        start_date, end_date = self.get_date_from_this_week_on()

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
    # app.fetch_event()
    
    my_calendar = app.get_or_create_calendar()
    print(my_calendar)

    # my_principal = app.connect()
    # print(my_principal)
    
