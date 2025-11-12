import os
from dotenv import load_dotenv
from datetime import datetime, date, time, timedelta

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

    def get_week_from_today(self):
        """Get lesson week from today"""
        # Get today's date
        today = datetime.today().date()

        # Get the day difference
        days_difference = (today - FIRST_DAY).days
        
        # Calculate week number
        week_number = (days_difference // 7) + 1

        if self.debug:
            print(f"DEBUG: week_number: {week_number}")

        return week_number
        

# Local testing
if __name__ == "__main__":
    app = CalendarSchedule()
    app.debug = True

    app.get_week_from_today()