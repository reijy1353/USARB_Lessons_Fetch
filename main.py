"""
Main script to sync university schedule to iCloud Calendar using CalDAV.
"""
import os
import sys
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import caldav
from dotenv import load_dotenv

from data_parser import (
    calc_lesson_datetime,
    generate_event_id,
    WEEK_ZERO_START,
    calc_university_week_from_date,
    calc_date_from_week_and_day,
)
from raw_schedule_data_fetch import get_raw_schedule_json


# Load environment variables
load_dotenv()


class CalendarSync:
    """Handle syncing lessons to iCloud Calendar via CalDAV."""
    
    def __init__(self, caldav_url: str, username: str, password: str, calendar_name: str = "USARB Schedule"):
        """
        Initialize CalDAV connection.
        
        Args:
            caldav_url: iCloud CalDAV URL (e.g., https://caldav.icloud.com/)
            username: iCloud email address
            password: iCloud app-specific password
            calendar_name: Name of the calendar to sync to (will be created if doesn't exist)
        """
        self.caldav_url = caldav_url
        self.username = username
        self.password = password
        self.calendar_name = calendar_name
        self.client = None
        self.calendar = None
        
    def connect(self):
        """Connect to CalDAV server and get/create calendar."""
        try:
            # Connect to CalDAV server
            self.client = caldav.DAVClient(
                url=self.caldav_url,
                username=self.username,
                password=self.password
            )
            
            # Get principal (user's calendar collection)
            principal = self.client.principal()
            calendars = principal.calendars()
            
            # Find or create calendar
            self.calendar = None
            for cal in calendars:
                if cal.name == self.calendar_name:
                    self.calendar = cal
                    break
            
            # Create calendar if it doesn't exist
            if not self.calendar:
                print(f"Creating calendar: {self.calendar_name}")
                self.calendar = principal.make_calendar(name=self.calendar_name)
            else:
                print(f"Found existing calendar: {self.calendar_name}")
                
            return True
        except Exception as e:
            print(f"Error connecting to CalDAV: {e}")
            return False
    
    def get_existing_events(self, start_date: datetime, end_date: datetime) -> Dict[str, caldav.Event]:
        """
        Get existing events in the calendar within date range.
        Returns dict mapping event_id to event object.
        """
        if not self.calendar:
            return {}
        
        try:
            # Search for events in date range
            events = self.calendar.search(start=start_date, end=end_date)
            
            # Extract event IDs from UID by parsing raw iCal data
            existing_events = {}
            for event in events:
                try:
                    # Get raw iCal data
                    ical_data = event.data
                    if isinstance(ical_data, bytes):
                        ical_data = ical_data.decode('utf-8')
                    
                    # Extract UID using regex (handle both UID: and UID; formats)
                    uid_match = re.search(r'UID(?::|;)([^\r\n]+)', ical_data, re.IGNORECASE)
                    if uid_match:
                        uid = uid_match.group(1).strip()
                        # Extract event ID from UID (format: event_id@domain)
                        if '@' in uid:
                            event_id = uid.split('@')[0]
                            existing_events[event_id] = event
                except Exception as e:
                    print(f"Warning: Could not parse event UID: {e}")
                    continue
            
            return existing_events
        except Exception as e:
            print(f"Error fetching existing events: {e}")
            return {}
    
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
    
    def create_or_update_event(
        self,
        event_id: str,
        title: str,
        start_dt: datetime,
        end_dt: datetime,
        description: str = "",
        location: str = "",
    ):
        """
        Create or update a calendar event.
        Uses event_id as the UID for deduplication.
        """
        if not self.calendar:
            print("Error: Calendar not connected")
            return False
        
        try:
            # Escape values for iCal format
            safe_title = self._escape_ical_value(title)
            safe_description = self._escape_ical_value(description)
            safe_location = self._escape_ical_value(location)
            
            # Create UID (must be unique)
            uid = f"{event_id}@usarb-schedule.local"
            
            # Format datetime for iCal (local time, no timezone)
            dtstart = start_dt.strftime('%Y%m%dT%H%M%S')
            dtend = end_dt.strftime('%Y%m%dT%H%M%S')
            
            # Create iCal content with proper formatting
            # Each line should be max 75 characters (folded if longer)
            ical_lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//USARB Schedule//EN",
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{safe_title}",
            ]
            
            # Add description if present
            if safe_description:
                # iCal format: DESCRIPTION:value (can be folded if >75 chars)
                # For now, just add it - caldav will handle folding if needed
                ical_lines.append(f"DESCRIPTION:{safe_description}")
            
            # Add location if present
            if safe_location:
                ical_lines.append(f"LOCATION:{safe_location}")
            
            ical_lines.extend([
                "END:VEVENT",
                "END:VCALENDAR",
                ""  # Final newline
            ])
            
            # Join with CRLF (iCal standard)
            ical_content = "\r\n".join(ical_lines)
            
            # Save event using caldav
            try:
                self.calendar.save_event(
                    ical_content.encode('utf-8'),
                    object_id=f"{event_id}.ics"
                )
                return True
            except Exception as inner_e:
                # Treat 412 Precondition Failed as 'already exists' and continue
                if "412 Precondition Failed" in str(inner_e):
                    return True
                print(f"Error creating/updating event: {inner_e}")
                return False
        except Exception as e:
            pass
    
    def sync_lessons(
        self,
        group_name: str,
        weeks: Optional[List[int]] = None,
        start_week: Optional[int] = None,
        end_week: Optional[int] = None,
        overwrite: bool = True,
        debug: bool = False,
    ):
        """
        Sync lessons to calendar for specified weeks.
        
        Args:
            group_name: Group name (e.g., "IT11Z")
            weeks: List of specific weeks to sync (if None, uses start_week/end_week)
            start_week: First week to sync (inclusive)
            end_week: Last week to sync (inclusive)
            overwrite: If True, update existing events; if False, skip existing events
            debug: Enable debug output
        """
        if not self.calendar:
            if not self.connect():
                print("Failed to connect to calendar")
                return False
        
        # Determine which weeks to sync
        if weeks is None:
            if start_week is None or end_week is None:
                # Default: sync current week and next 4 weeks
                today = datetime.today().date()
                current_week = calc_university_week_from_date(today)
                weeks = list(range(current_week, min(current_week + 5, 20)))  # Max 20 weeks
            else:
                weeks = list(range(start_week, end_week + 1))
        
        if debug:
            print(f"Syncing weeks: {weeks}")
        
        # Calculate date range for fetching existing events
        start_date = calc_date_from_week_and_day(min(weeks), 1)
        end_date = calc_date_from_week_and_day(max(weeks), 7) + timedelta(days=1)
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
        
        # Get existing events
        existing_events = self.get_existing_events(start_dt, end_dt) if overwrite else {}
        
        # Process each week
        total_events = 0
        created = 0
        updated = 0
        skipped = 0
        
        for week in weeks:
            if debug:
                print(f"\nProcessing week {week}...")
            
            try:
                # Fetch schedule data
                raw_data = get_raw_schedule_json(group_name, university_week=week, debug=debug)
                entries = raw_data.get("week") or []
                
                for lesson in entries:
                    day_number = lesson.get("day_number", 0)
                    lesson_number = lesson.get("cours_nr", 0)
                    cours_name = lesson.get("cours_name", "")
                    cours_type = lesson.get("cours_type", "")
                    cours_office = lesson.get("cours_office", "")
                    teacher = lesson.get("teacher_name", "")
                    
                    if day_number == 0 or lesson_number == 0:
                        continue
                    
                    # Generate event ID
                    event_id = generate_event_id(
                        group_name, week, day_number, lesson_number,
                        cours_name, cours_type
                    )
                    
                    # Check if event already exists
                    event_exists = event_id in existing_events
                    if event_exists and not overwrite:
                        skipped += 1
                        if debug:
                            print(f"  Skipping existing event: {cours_name}")
                        continue
                    
                    # Calculate datetime
                    start_dt, end_dt = calc_lesson_datetime(week, day_number, lesson_number)
                    
                    # Create event title
                    title = f"{cours_name} | {cours_type}" if cours_type else cours_name
                    
                    # Create description
                    description_parts = [
                        f"Lesson {lesson_number}",
                        f"Type: {cours_type}" if cours_type else "",
                        f"Office: {cours_office}" if cours_office else "Unknown",
                        f"Teacher: {teacher}" if teacher else "",
                    ]
                    description = "\n".join([p for p in description_parts if p])
                    
                    # Location
                    location = cours_office if cours_office else "Unknown"
                    
                    # Delete existing event if updating
                    if event_exists and overwrite:
                        try:
                            existing_events[event_id].delete()
                        except Exception as e:
                            if debug:
                                print(f"  Warning: Could not delete existing event: {e}")
                    
                    # Create or update event
                    if self.create_or_update_event(
                        event_id, title, start_dt, end_dt, description, location
                    ):
                        if event_exists:
                            updated += 1
                            if debug:
                                print(f"  Updated: {title} on {start_dt.date()}")
                        else:
                            created += 1
                            if debug:
                                print(f"  Created: {title} on {start_dt.date()}")
                        total_events += 1
                    else:
                        print(f"  Failed to create: {title}")
                        
            except Exception as e:
                print(f"Error processing week {week}: {e}")
                if debug:
                    import traceback
                    traceback.print_exc()
        
        print(f"\nSync complete!")
        print(f"  Total events: {total_events}")
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")
        print(f"  Skipped: {skipped}")
        
        return True


def main():
    """Main function."""
    # Get configuration from environment variables
    caldav_url = os.getenv("CALDAV_URL", "https://caldav.icloud.com/")
    username = os.getenv("ICLOUD_USERNAME")
    password = os.getenv("ICLOUD_PASSWORD")
    calendar_name = os.getenv("CALENDAR_NAME", "USARB Schedule")
    group_name = os.getenv("GROUP_NAME", "IT11Z")
    
    # Check required credentials
    if not username or not password:
        print("Error: ICLOUD_USERNAME and ICLOUD_PASSWORD must be set in environment variables or .env file")
        print("\nTo set up:")
        print("1. Create a .env file in the project root")
        print("2. Add the following:")
        print("   CALDAV_URL=https://caldav.icloud.com/")
        print("   ICLOUD_USERNAME=your.email@icloud.com")
        print("   ICLOUD_PASSWORD=your-app-specific-password")
        print("   CALENDAR_NAME=USARB Schedule")
        print("   GROUP_NAME=IT11Z")
        print("\nNote: For iCloud, use an app-specific password, not your regular password.")
        print("      Generate one at: https://appleid.apple.com/")
        sys.exit(1)
    
    # Initialize calendar sync
    sync = CalendarSync(caldav_url, username, password, calendar_name)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Sync university schedule to iCloud Calendar")
    parser.add_argument("--group", type=str, default=group_name, help="Group name (e.g., IT11Z)")
    parser.add_argument("--weeks", type=str, help="Comma-separated list of weeks (e.g., 1,2,3)")
    parser.add_argument("--start-week", type=int, help="Start week (inclusive)")
    parser.add_argument("--end-week", type=int, help="End week (inclusive)")
    parser.add_argument("--no-overwrite", action="store_true", help="Don't update existing events")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    # Parse weeks
    weeks = None
    if args.weeks:
        weeks = [int(w.strip()) for w in args.weeks.split(",")]
    
    # Sync
    sync.sync_lessons(
        group_name=args.group,
        weeks=weeks,
        start_week=args.start_week,
        end_week=args.end_week,
        overwrite=not args.no_overwrite,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()

