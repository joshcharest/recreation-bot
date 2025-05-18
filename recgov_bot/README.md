# Recreation.gov Booking Bot

An automated booking system for Recreation.gov that helps secure permits and reservations when they become available.

## Features

- Automated login to Recreation.gov
- Configurable date, group size, and location settings
- Automatic date selection and booking attempt
- Continuous retry functionality until successful booking
- Timezone-aware scheduling
- Detailed logging

## Requirements

- Python 3.6+
- Chrome browser
- ChromeDriver
- Required Python packages:
  - selenium
  - pytz
  - logging
  - json
  - datetime

## Installation

1. Clone this repository
2. Install required packages:
```bash
pip install selenium pytz
```
3. Download ChromeDriver matching your Chrome version
4. Create a config.json file (see Configuration section)

## Configuration

Create a `config.json` file with the following structure:

```json
{
    "username": "your_email@example.com",
    "password": "your_password",
    "url": "recreation.gov_booking_page_url",
    "start_date": "YYYY-MM-DD",
    "num_people": "2",
    "trailhead": "Trailhead Name",
    "timezone": "America/Los_Angeles",
    "start_time": "07:00"
}
```

## Usage

Run the bot:

```bash
python recreation_bot.py
```

The bot will:
1. Log into Recreation.gov
2. Navigate to the specified booking page
3. Wait until the configured start time
4. Attempt to make a reservation
5. Retry booking for up to 22 minutes if unsuccessful

## Limitations

- Requires stable internet connection
- Chrome browser must be installed
- May be affected by Recreation.gov website changes
- Does not handle CAPTCHA challenges

## Security Notes

Store your credentials securely and never commit config.json to version control.
