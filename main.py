import os
import json
from re import S
from typing import Any
from dotenv import load_dotenv
from datetime import datetime, date, time, timedelta
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

    def get_date_from_this_week_on(self, postpone: int, week: int = None) -> Any | None:
        """Get a range of dates, from first day of the university week, to the 
        one calculated by formula week + postpone (e.g. week = 10, postone = 3)
        returns the range from start of week 10, till then end of week 10 + 3 = 13.

        Args:
            week (int): This week
            postpone (int): How many weeks on you want to prolong your calendar

        Returns:
            start_date: The date of the first day of the first week
            end_date: The last day of the last week (calculated from week+postpone)
        """
        # If no week is given, use "this" week by default
        if week is None:
            week = self.get_this_week()
            print(f"week var wasn't given, setting up this week by default (week = {week})")

        # Get the start_date
        # formula: start_date = FIRST_DAY + 7 * week
        start_date = FIRST_DAY + timedelta(days=7) * (week - 1)

        # Get the end_date
        # forumula: end_date = (start_date + 7 * postpone) - 1
        end_date = (start_date + timedelta(days=7) * postpone) - timedelta(days=1)

        # Debug
        if self.debug:
            print(f"DEBUG: start_date = {start_date}")
            print(f"DEBUG: end_date = {end_date}")
        
        return start_date, end_date

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
            print(f"DEBUG: data from json: {schedule_snapshot}")
        
        return schedule_snapshot
        
    def get_calendar(self):
        """Get the calendar that you'll be using for your Schedule (from .env)

        Returns:
            my_calendar: Your calendar
        """
        with get_davclient(
            username=self.username,
            password=self.password,
            url=self.caldav_url   
        ) as client:
        
            my_principal = client.principal()

            try:
                my_calendar = my_principal.calendar(name=self.calendar_name)
            except NotFoundError:
                print(f"You don't seem to have a calendar named {self.calendar_name}")
                return None
                
            if self.debug:
                print(f"DEBUG: type {type(my_calendar)}")
                print(f"DEBUG: calendar {my_calendar}")
        
            return my_calendar
        
# Local testing
if __name__ == "__main__":
    app = CalendarSchedule()
    app.debug = True

    app.get_date_from_this_week_on(3)
