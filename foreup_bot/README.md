# ForeUp Golf Tee Time Bot

A Python-based automation tool for booking golf tee times on ForeUp-powered golf course websites.

## 🏗️ Directory Structure

```
foreup_bot/
├── core/                    # Core bot functionality
│   ├── foreup_bot.py       # Main bot implementation
│   └── config_gui.py       # Configuration GUI
├── aws/                    # AWS deployment and management
│   ├── deploy_aws.py       # Deploy to AWS Lambda
│   ├── cleanup_aws.py      # Clean up AWS resources
│   ├── create_lambda_layer.py
│   └── subscribe_notifications.py
├── monitoring/             # Monitoring and status checking
│   ├── monitoring_service.py
│   ├── lambda_monitor.py
│   ├── run_monitoring.py
│   └── setup_monitoring.py
├── utils/                  # Utility scripts
│   ├── check_status.py     # AWS status checking
│   └── quick_start.py      # Quick setup wizard
├── config/                 # Configuration files
│   ├── foreup_config.json
│   └── credentials_template.json
├── run.py                  # Main launcher script
├── VERSION                 # Version information
└── README_MONITORING.md    # Monitoring documentation
```

## 🚀 Quick Start

1. **Setup**: Run the quick start wizard
   ```bash
   python run.py
   # Select option 7: Quick Start Setup
   ```

2. **Configure**: Edit your credentials in `config/credentials.json`

3. **Run**: Start the bot
   ```bash
   python run.py
   # Select option 1: Run Main Bot
   ```

## 📋 Features

- **Automated Booking**: Automatically books tee times based on your preferences
- **AWS Integration**: Deploy as a serverless Lambda function
- **Monitoring**: Real-time monitoring and notifications
- **GUI Configuration**: Easy-to-use configuration interface
- **Status Checking**: Monitor AWS deployment health

## 🔧 Configuration

### Main Configuration (`config/foreup_config.json`)
```json
{
  "booking": {
    "preferred_times": ["07:00", "08:00", "09:00"],
    "preferred_days": ["Saturday", "Sunday"],
    "max_players": 4
  },
  "monitoring": {
    "check_interval": 300,
    "sns_topic_arn": "arn:aws:sns:us-east-1:..."
  }
}
```

### Credentials (`config/credentials.json`)
```json
{
  "username": "your_email@example.com",
  "password": "your_password"
}
```

## ☁️ AWS Deployment

1. **Deploy**: Deploy to AWS Lambda
   ```bash
   python run.py
   # Select option 3: Deploy to AWS
   ```

2. **Monitor**: Check deployment status
   ```bash
   python run.py
   # Select option 6: Check AWS Status
   ```

3. **Cleanup**: Remove AWS resources
   ```bash
   python run.py
   # Select option 4: Clean up AWS Resources
   ```

## 📊 Monitoring

The bot includes comprehensive monitoring capabilities:

- **Local Monitoring**: Run monitoring locally for testing
- **AWS Monitoring**: Cloud-based monitoring with SNS notifications
- **Status Dashboard**: Check health of all AWS components

See `README_MONITORING.md` for detailed monitoring documentation.

## 🛠️ Development

### Prerequisites
- Python 3.8+
- Chrome browser
- AWS CLI (for cloud deployment)

### Dependencies
```bash
pip install -r requirements.txt
```

### Running Tests
```bash
# Add test commands here when implemented
```

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here] 