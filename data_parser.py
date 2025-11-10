
pass

from raw_schedule_data_fetch import get_raw_schedule_data

# ! will be using md5 for event ID's (https://chatgpt.com/share/691252a6-d8f8-8003-a3ec-aadcfc3c2329)




if __name__ == "__main__":
    data = get_raw_schedule_data("IT11Z", university_week=11, debug=False)

    mapping = {        
        1: "monday",
        2: "tuesday",
        3: "wednesday",
        4: "thursday",
        5: "friday",
        6: "saturday",
    }
    
    parsed_data = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "saturday": [],
    }
    
    for i in data["week"]:
        parsed_data[mapping[i["day_number"]]].append(i)
        
    for day, lessons in parsed_data.items():
        if parsed_data[day]:
            print(f"\nOn {day.upper()} you have:")
            for lesson in lessons:
                print(f"Lesson {lesson["cours_nr"]} | {lesson["teacher_name"]} |"
                    f"aud. {lesson["cours_office"] if lesson["cours_office"] else "Unknown"}") 

    # How will the json/dict of lessons look
    lessons = {
        "11": {
            "hash1" : {
                "lesson_day": "",
                "lesson_nr": "",
                "lesson_name": "",
                "lesson_type": "",
                "office_nr": "",
                "teacher_name": "",
                
            },
            "hash2": {},
        },
        "12": {}, # 11 and 12 are the number of the week
    }