import requests
from bs4 import BeautifulSoup

# Initialize the session
session = requests.Session()

# URL of the main page
url_main = "https://orar.usarb.md"

# Get the home page (for cookies + csrf)
r = session.get(url_main)

# Get the CSRF token
def get_csrf():
    soup: BeautifulSoup = BeautifulSoup(r.text, "html.parser")
    csrf: str = soup.find("meta", {"name": "csrf-token"})["content"]
    return csrf

# Get the schedule
def get_raw_schedule_json(your_group_name: str, semester: int = 1, university_week: int = 1, debug: bool = False):
    # Get CSRF token
    csrf = get_csrf()

    # Get the group ID by name
    group_id = _get_groups_by_name(your_group_name, csrf)
    
    # Prepare POST data
    data = {
        "_csrf": csrf,
        "gr": group_id,
        "sem": semester,
        "day": 7, # Only the frontend needs that.
        "week": university_week,
        "grName": f"{your_group_name}"
    }
    
    # Get lessons data
    r_lessons = _get_lessons_json(data, debug=debug)

    # Return the raw json data
    return r_lessons
    
# Get the user's group ID by name
def _get_groups_by_name(group_name: str, csrf: str, debug: bool = False):
    # Get URL
    url_groups = f"{url_main}/api/getGroups"
    
    # Prepare POST data
    data = {
        "_csrf": csrf,
    }
    
    # POST to get groups
    r_groups = session.post(url_groups, data=data)

    # Debugging
    if debug:
        print("Status groups:", r_groups.status_code)
        print("Response groups:", r_groups.json())
    
    # Get the group ID from the response
    for group in r_groups.json():
        if group["Denumire"] == group_name:
            return group["Id"]

    # If the group is not found, return None
    return None

# Get the user's lessons
def _get_lessons_json(data: dict, debug: bool = False):
    # Get URL
    url_lessons = f"{url_main}/api/getlessons"

    # POST to get lessons
    r_lessons = session.post(url_lessons, data=data)

    # Debugging
    if debug:
        print("Status lessons:", r_lessons.status_code)
        print("Response lessons:", r_lessons.json())
    
    # Return the lessons
    return r_lessons.json()


if __name__ == "__main__":
    get_raw_schedule_json("IT11Z", debug=True)