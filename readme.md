# 📅 USARB Schedule Automation

> Automatically sync your university schedule from [orar.usarb.md](https://orar.usarb.md/) directly to your iCloud Calendar using CalDAV.

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Personal%20Use-lightgrey.svg)]()

---

## ✨ Features

- 🔄 **Automatic Schedule Sync** - Fetches your weekly schedule from the USARB portal
- 📱 **iCloud Calendar Integration** - Directly syncs events to your iCloud Calendar via CalDAV
- 🎯 **Smart Event Management** - Automatically creates or updates calendar events with lesson details
- 📊 **Multi-Week Support** - Sync multiple weeks ahead (default: current week + 3 weeks)
- 🔍 **Detailed Event Information** - Includes lesson name, type, location, teacher, and time
- 💾 **Snapshot Support** - Save and load schedule snapshots for offline access
- 🛡️ **CSRF Protection** - Handles CSRF tokens and session management automatically

---

## 🚀 Quick Start

### Prerequisites

- Python 3.x
- iCloud account with CalDAV access enabled
- USARB student account (access to orar.usarb.md)

### Installation

1. **Clone or download this repository**

```bash
git clone <repository-url>
cd usarb_schedule_fetch
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file in the project root with the following variables:

```env
# iCloud CalDAV Configuration
CALDAV_URL=https://caldav.icloud.com
ICLOUD_USERNAME=your_apple_id@icloud.com
ICLOUD_PASSWORD=your_app-specific_password
CALENDAR_NAME=USARB Schedule

# University Configuration
GROUP_NAME=IT11Z
```

> **Note:** For iCloud, you'll need to generate an [App-Specific Password](https://support.apple.com/en-us/102654) instead of your regular Apple ID password.

---

## 📖 Usage

### Basic Usage

Run the main script to sync your schedule:

```bash
python main.py
```

This will:
1. Fetch your schedule for the current week and the next 2 weeks
2. Create or update events in your specified iCloud Calendar
3. Automatically handle lesson times, locations, and teacher information

### Advanced Usage

#### Custom Week Range

You can modify the code to sync specific weeks:

```python
from main import CalendarSchedule

app = CalendarSchedule()
# Sync weeks 10, 11, and 12
app.parse_schedule_data(weeks=[10, 11, 12])
```

#### Save Schedule Snapshot

Save your schedule to a JSON file for offline access:

```python
from data_parser import save_schedule_to_json

# Save weeks 10, 11, 12 to schedule_snapshot.json
save_schedule_to_json("IT11Z", 10, 11, 12)
```

#### Load Schedule from Snapshot

```python
from main import CalendarSchedule

app = CalendarSchedule()
schedule_data = app.get_data_from_snapshot("schedule_snapshot.json")
```

---

## 📁 Project Structure

```
usarb_schedule_fetch/
├── main.py                      # Main calendar sync logic
├── raw_schedule_data_fetch.py   # Web scraping and API calls
├── data_parser.py               # Schedule parsing and snapshot utilities
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (create this)
├── schedule_snapshot.json       # Optional: saved schedule snapshot
└── readme.md                    # This file
```

### Key Components

- **`CalendarSchedule`** (`main.py`) - Main class handling calendar operations
  - Connects to iCloud via CalDAV
  - Parses schedule data into iCal format
  - Manages calendar events

- **`get_raw_schedule_data()`** (`raw_schedule_data_fetch.py`) - Fetches schedule from USARB API
  - Handles CSRF token extraction
  - Manages session cookies
  - Queries the internal API

- **`data_parser.py`** - Utility functions for schedule manipulation
  - Generates unique lesson IDs
  - Creates schedule snapshots
  - Organizes schedule data by week and day

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CALDAV_URL` | Your CalDAV server URL | `https://caldav.icloud.com` |
| `ICLOUD_USERNAME` | Your Apple ID email | `user@icloud.com` |
| `ICLOUD_PASSWORD` | App-specific password | `xxxx-xxxx-xxxx-xxxx` |
| `CALENDAR_NAME` | Name of the calendar to use/create | `USARB Schedule` |
| `GROUP_NAME` | Your university group name | `IT11Z` |

### Calendar Settings

The script automatically:
- Creates a new calendar if one with the specified name doesn't exist
- Uses UTC timezone for all events
- Sets lesson duration to 1 hour 30 minutes
- Calculates lesson times based on the first lesson starting at 8:00 AM

### Week Calculation

Weeks are calculated from September 1, 2025 (Week 1). The script automatically determines the current week based on today's date.

---

## 🔧 Troubleshooting

### Common Issues

**Problem:** `ConnectionError` or authentication failures
- **Solution:** Verify your CalDAV URL and ensure you're using an App-Specific Password for iCloud

**Problem:** `NotFoundError` for group name
- **Solution:** Check that your `GROUP_NAME` matches exactly as it appears on the USARB portal

**Problem:** Events not appearing in calendar
- **Solution:** 
  - Check that the calendar name in `.env` matches your iCloud calendar
  - Verify CalDAV is enabled for your iCloud account
  - Check script output for error messages

**Problem:** CSRF token errors
- **Solution:** The script handles this automatically, but if issues persist, ensure you have internet connectivity and the USARB portal is accessible

### Debug Mode

Enable debug mode to see detailed output:

```python
app = CalendarSchedule()
app.debug = True
app.parse_schedule_data()
```

---

## 📋 Dependencies

Key dependencies include:
- `caldav` - CalDAV client for calendar operations
- `requests` - HTTP requests for web scraping
- `beautifulsoup4` - HTML parsing for CSRF token extraction
- `python-dotenv` - Environment variable management
- `icalendar` - iCal format handling

See `requirements.txt` for the complete list.

---

## 🔐 Security Notes

- Never commit your `.env` file to version control
- Use App-Specific Passwords for iCloud (not your main Apple ID password)
- Keep your credentials secure and private

---

## 📝 License

This project is for personal use only.

---

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

---

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](#-troubleshooting) section
2. Review the code comments for implementation details
3. Enable debug mode to see detailed execution logs

---

**Made with ❤️ for USARB students**
