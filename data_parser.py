import hashlib
import json
from collections import defaultdict
from typing import Any

from raw_schedule_data_fetch import get_raw_schedule_data

def get_lesson_hash(lesson_day: int, lesson_nr: int, lesson_name: str, lesson_type: str, office: int, teacher: str, debug: bool = False):
    """Returning a 32 character hash created using MD5 and a string from the given args

    Args:
        lesson_day (int): lesson day
        lesson_nr (int): lessons number
        lesson_name (str): lesson name
        lesson_type (str): lesson type
        office (int): office
        teacher (str): teacher
        debug (bool, optional): debug. Defaults to False.

    Returns:
        _type_: hash
    """
    to_hash = f"{lesson_day}{lesson_nr}{lesson_name}{lesson_type}{office}{teacher}"
    hash = hashlib.md5(to_hash.encode()).hexdigest()[:32]
    
    if debug:
        print(f"DEBUG: {hash}")

    return hash

    
def get_schedule(group_name: str, *weeks: int, debug: bool = False):
    """All the specifications/keywords we need:
        cours_nr -> lesson number (1 - 8)
        cours_name -> name of the course/class (e.g. Math)
        cours_office -> locatin (e.g. 224)
        teacher_name -> name of the teacher (e.g. Cernolev C.)
        cours_type -> type of any course (e.g. Prelegere, Seminar etc.)
        day_number -> the day when it happends (1-7, we'll be needing/using just 1-6, don't think you want to study on Sundays)
        week -> number of the week (relatively from 01.09.2025, which was week 1)

    Args:
        group_name (str): name of your group (the group you're in)
        debug (bool, optional): debug. Defaults to False.

    Returns:
        _type_: _description_
    """

    # If a single argument is a list or tuple, unpack it
    if len(weeks) == 1 and isinstance(weeks[0], (list, tuple)):
        weeks = weeks[0]
    
    # Create a dict for saving schedule
    schedule = defaultdict[Any, defaultdict[Any, dict]](lambda: defaultdict[Any, dict](dict))
    
    for week in weeks:
        # Get the raw schedule
        raw_schedule = get_raw_schedule_data(group_name, university_week=week)

        # Create a dict that will save every lesson by thei day (1-7, monday-sunday)
        lessons_by_day = {
            1: [],
            2: [],
            3: [],
            4: [],
            5: [],
            6: [],
            7: [],
        }
        
        # Save lessons to lessons_by_day dict
        for i in raw_schedule["week"]:
            lessons_by_day[i["day_number"]].append(i)    
            
        # DEBUG
        if debug:
            print(f"\n\nDEBUG lessons_by_day: {lessons_by_day}")

        # Loop for saving lessons to schedule (here we're getting all the lessons for a day)
        for lessons in lessons_by_day.values():

            # DEBUG
            if debug:
                print(f"\n\nDEBUG lessons: {lessons}")

            # Getting the lessons one by one from lessons
            for lesson in lessons:
                lesson_day = lesson["day_number"]
                lesson_nr = lesson["cours_nr"]
                lesson_name = lesson["cours_name"]
                lesson_type = lesson["cours_type"]
                office = lesson["cours_office"]
                teacher = lesson["teacher_name"]
                
                # Get the lesson hash
                lesson_hash = get_lesson_hash(lesson_day, lesson_nr, lesson_name, lesson_type, office, teacher)
                
                # Write everyting in the schedule dict
                schedule[week][lesson_hash]["lesson_day"] = lesson_day
                schedule[week][lesson_hash]["lesson_nr"] = lesson_nr
                schedule[week][lesson_hash]["lesson_name"] = lesson_name
                schedule[week][lesson_hash]["lesson_type"] = lesson_type
                schedule[week][lesson_hash]["office"] = office
                schedule[week][lesson_hash]["teacher"] = teacher
                
                # DEBUG
                if debug:
                    print(f"\n\nDEBUG schedule by lesson_hash: f{schedule[week][lesson_hash]}")

    # DEBUG
    if debug:
        print(f"\n\nDEBUG schedule itself: {schedule}")

    # Return the schedule
    return schedule
                    

def save_schedule_to_json(group_name: str, *weeks: int, debug: bool = False):
    """Saving the schedule retrieved from get_schedule() function to schedule_snapshot.json
        (overwriting it it already exists)

    Args:
        group_name (str): your group name
        debug (bool, optional): debug. Defaults to False.
    """
    
    schedule = get_schedule(group_name, *weeks)

    with open("schedule_snapshot.json", "w") as f:
        json.dump(schedule, f, indent=4)
        

# Local testing
if __name__ == "__main__":
    save_schedule_to_json("IT11Z", (10, 11, 12))