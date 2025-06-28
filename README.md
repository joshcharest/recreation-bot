# Recreation Booking Bots

A collection of automated booking bots for various recreation platforms, designed to help secure permits, reservations, and tee times when they become available.

## Overview

This repository contains three specialized booking bots:

- **Recreation.gov Bot** - For national park permits and camping reservations
- **ForeUp Golf Bot** - For golf tee time bookings on ForeUp-powered courses
- **ReserveCA Bot** - For California state park camping reservations

## Features

### Recreation.gov Bot
- Automated login to Recreation.gov
- Configurable date, group size, and location settings
- Automatic date selection and booking attempt
- Continuous retry functionality until successful booking
- Timezone-aware scheduling
- Detailed logging

### ForeUp Golf Bot
- Automated login to ForeUp-powered golf course websites
- GUI configuration interface for easy setup
- Configurable date, number of players, and target time
- Time window selection for flexible booking preferences
- Automatic tee time selection based on preferences
- Continuous retry with intelligent time matching

### ReserveCA Bot
- Automated login to ReserveCalifornia.com
- Support for multi-day camping reservations
- Configurable campsite preferences
- Date range selection (start and end dates)
- Automatic campsite availability checking
- CAPTCHA handling capabilities

## Requirements

- Python 3.6+
- Chrome browser
- ChromeDriver (automatically managed by webdriver-manager)
- Required Python packages (see requirements.txt):
  - selenium==4.18.1
  - pytz>=2023.3
  - webdriver-manager==4.0.1
  - tkcalendar==1.6.1

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd recreation
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

### Recreation.gov Bot

Create a `recgov_bot/recgov_config.json` file:

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

### ForeUp Golf Bot

1. Create a `foreup_bot/foreup_config.json` file:
```json
{
    "target_date": "MM-DD-YYYY",
    "num_players": 4,
    "start_time": "10:00 AM",
    "window_start_time": "09:00 AM",
    "window_end_time": "11:00 AM"
}
```

2. Create a `credentials/foreup_credentials.json` file:
```json
{
    "username": "your_email@example.com",
    "password": "your_password"
}
```

3. (Optional) Use the GUI configuration tool:
```bash
python foreup_bot/config_gui.py
```

### ReserveCA Bot

1. Create a `reserve_ca_bot/res_ca_config.json` file:
```json
{
    "url": "https://www.reservecalifornia.com/Web/",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "campsite": "Campsite Name"
}
```

2. Create a `credentials/reserve_ca_credentials.json` file:
```json
{
    "username": "your_email@example.com",
    "password": "your_password"
}
```

## Usage

### Recreation.gov Bot

```bash
cd recgov_bot
python recreation.py
```

The bot will:
1. Log into Recreation.gov
2. Navigate to the specified booking page
3. Wait until the configured start time
4. Attempt to make a reservation
5. Retry booking for up to 22 minutes if unsuccessful

### ForeUp Golf Bot

```bash
cd foreup_bot
python foreup_bot.py
```

The bot will:
1. Log into the ForeUp booking system
2. Navigate to the tee time booking page
3. Set the target date and number of players
4. Find available times within the specified window
5. Select the closest time to your target
6. Complete the booking process

### ReserveCA Bot

```bash
cd reserve_ca_bot
python reserve_ca.py
```

The bot will:
1. Log into ReserveCalifornia.com
2. Navigate to the camping reservation page
3. Set the date range for your stay
4. Search for available campsites
5. Attempt to book the specified campsite
6. Handle any CAPTCHA challenges

## Project Structure

```
recreation/
├── recgov_bot/              # Recreation.gov booking bot
│   ├── recreation.py        # Main bot implementation
│   └── recgov_config.json   # Configuration file
├── foreup_bot/              # ForeUp golf booking bot
│   ├── foreup_bot.py        # Main bot implementation
│   ├── config_gui.py        # GUI configuration tool
│   └── foreup_config.json   # Configuration file
├── reserve_ca_bot/          # ReserveCA camping bot
│   ├── reserve_ca.py        # Main bot implementation
│   └── res_ca_config.json   # Configuration file
├── credentials/             # Credential files (not in version control)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Security Notes

- **Never commit credential files to version control**
- Store credentials securely in the `credentials/` directory
- Use environment variables for sensitive data in production
- Regularly update your passwords and API keys

## Limitations

- Requires stable internet connection
- Chrome browser must be installed
- May be affected by website changes
- Some platforms may have rate limiting or anti-bot measures
- CAPTCHA challenges may require manual intervention

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational purposes. Please ensure compliance with the terms of service of the platforms you're automating.

## Disclaimer

These bots are provided as-is for educational purposes. Users are responsible for ensuring their use complies with the terms of service of the respective platforms. The authors are not responsible for any misuse or violations of platform policies.
