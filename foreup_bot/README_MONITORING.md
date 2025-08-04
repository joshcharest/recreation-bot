# ForeUp Bot Monitoring Documentation

This document provides detailed information about the monitoring capabilities of the ForeUp Golf Tee Time Bot, including AWS deployment, local monitoring, and status checking.

## 📊 Monitoring Overview

The ForeUp bot includes comprehensive monitoring capabilities that can run both locally and in the cloud:

- **Local Monitoring**: For testing and development
- **AWS Monitoring**: Production-ready serverless monitoring
- **Status Dashboard**: Real-time health checking of all components

## 🏗️ AWS Monitoring Architecture

### Components

1. **AWS Lambda Function** (`ForeUpMonitor`)
   - Runs the monitoring logic
   - Triggered by EventBridge on a schedule
   - Publishes results to SNS

2. **EventBridge Rule** (`ForeUpMonitorSchedule`)
   - Triggers monitoring at configurable intervals
   - Default: Every 15 minutes

3. **SNS Topic** (`ForeUpMonitorTopic`)
   - Sends notifications when availability is found
   - Supports email and SMS subscriptions

4. **CloudWatch**
   - Logs: Detailed execution logs
   - Metrics: Performance and availability metrics
   - Alarms: Automated alerting

### Cost Estimation

- **Lambda**: ~$0.20 per million requests
- **EventBridge**: $1.00 per million events  
- **CloudWatch**: $0.50 per million metrics
- **SNS**: $0.50 per million notifications

**Total**: $1-5/month for continuous monitoring

## 🚀 Deployment

### Prerequisites

1. **AWS CLI Configuration**
   ```bash
   aws configure
   # Set your AWS credentials and region (us-east-1 recommended)
   ```

2. **Required Permissions**
   - Lambda: Create/update functions
   - IAM: Create roles and policies
   - EventBridge: Create rules
   - SNS: Create topics and subscriptions
   - CloudWatch: Create log groups and metrics

### Deployment Steps

1. **Deploy to AWS**
   ```bash
   python run.py
   # Select option 3: Deploy to AWS
   ```

2. **Subscribe to Notifications**
   ```bash
   python run.py
   # Select option 5: Subscribe to Notifications
   ```

3. **Verify Deployment**
   ```bash
   python run.py
   # Select option 6: Check AWS Status
   ```

## 📋 Configuration

### Monitoring Configuration

Edit `config/foreup_config.json`:

```json
{
  "monitoring": {
    "enabled": true,
    "check_interval_minutes": 15,
    "aws_region": "us-east-1",
    "sns_topic_arn": "arn:aws:sns:us-east-1:...",
    "cloudwatch_namespace": "ForeUpBot/Monitoring",
    "notification_email": "your-email@example.com"
  }
}
```

### Environment Variables

The deployment script automatically sets these environment variables:

- `AWS_PROFILE`: "personal" (configurable)
- `AWS_DEFAULT_REGION`: "us-east-1"
- `PYTHONPATH`: Includes required dependencies

## 🔍 Status Checking

### Available Checks

1. **Lambda Function Status**
   - Function state and configuration
   - Runtime and handler information
   - Last modification time

2. **EventBridge Rule Status**
   - Rule state and schedule
   - Trigger configuration

3. **SNS Topic Status**
   - Topic ARN and subscriptions
   - Subscription status

4. **CloudWatch Logs**
   - Recent log streams
   - Latest execution logs
   - Error patterns

5. **CloudWatch Metrics**
   - Available tee times found
   - Check success rate
   - Performance metrics

### Running Status Checks

```bash
# Check all components
python run.py
# Select option 6: Check AWS Status

# Or run directly
python utils/check_status.py
```

## 📊 Metrics and Logging

### CloudWatch Metrics

The monitoring service publishes these metrics:

- **AvailableTeeTimes**: Number of available times found
- **CheckSuccess**: Whether checks are successful (0/1)
- **ExecutionTime**: Time taken for each check
- **Errors**: Number of errors encountered

### Log Structure

Logs include:
- Timestamp and log level
- Function execution details
- Booking availability results
- Error messages and stack traces

### Example Log Entry

```
2024-01-15 10:30:00 - INFO - Starting monitoring check
2024-01-15 10:30:05 - INFO - Found 3 available tee times
2024-01-15 10:30:06 - INFO - Sending notification to SNS
2024-01-15 10:30:07 - INFO - Monitoring check completed successfully
```

## 🔧 Troubleshooting

### Common Issues

1. **Lambda Function Errors**
   ```bash
   # Check logs
   aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/ForeUpMonitor"
   aws logs tail /aws/lambda/ForeUpMonitor --follow
   ```

2. **EventBridge Rule Not Triggering**
   ```bash
   # Check rule status
   aws events describe-rule --name ForeUpMonitorSchedule
   ```

3. **SNS Notifications Not Received**
   ```bash
   # Check subscription status
   aws sns list-subscriptions-by-topic --topic-arn your-topic-arn
   ```

4. **Permission Errors**
   ```bash
   # Verify IAM roles
   aws iam get-role --role-name ForeUpMonitorRole
   ```

### Debug Mode

Enable debug logging by setting the log level in the Lambda function:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Local Testing

Test monitoring locally before deploying:

```bash
python run.py
# Select option 2: Run Local Monitoring
```

## 🧹 Cleanup

### Remove All AWS Resources

```bash
python run.py
# Select option 4: Clean up AWS Resources
```

This removes:
- Lambda function and role
- EventBridge rule
- SNS topic and subscriptions
- CloudWatch log groups
- IAM policies

### Manual Cleanup

If the automated cleanup fails:

```bash
# Remove Lambda
aws lambda delete-function --function-name ForeUpMonitor

# Remove EventBridge rule
aws events delete-rule --name ForeUpMonitorSchedule

# Remove SNS topic
aws sns delete-topic --topic-arn your-topic-arn

# Remove IAM role
aws iam delete-role --role-name ForeUpMonitorRole
```

## 🔒 Security Best Practices

1. **Credentials Management**
   - Use AWS Secrets Manager for production
   - Rotate credentials regularly
   - Use least-privilege IAM policies

2. **Network Security**
   - Use VPC for Lambda if needed
   - Configure security groups appropriately
   - Enable CloudTrail for audit logging

3. **Monitoring Security**
   - Encrypt SNS messages
   - Use HTTPS for all communications
   - Monitor access logs

## 📈 Performance Optimization

1. **Lambda Configuration**
   - Set appropriate timeout (30-60 seconds)
   - Configure memory based on workload
   - Use provisioned concurrency for consistent performance

2. **Monitoring Frequency**
   - Balance between responsiveness and cost
   - Consider different schedules for peak vs off-peak
   - Use adaptive intervals based on availability patterns

3. **Error Handling**
   - Implement retry logic with exponential backoff
   - Set up dead letter queues for failed executions
   - Monitor error rates and patterns

## 🔮 Future Enhancements

- [ ] Multi-course monitoring
- [ ] Dynamic scheduling based on availability patterns
- [ ] Web dashboard for monitoring status
- [ ] Mobile push notifications
- [ ] Integration with calendar systems
- [ ] Historical availability tracking
- [ ] Predictive availability modeling

---

**For support and questions, refer to the main README.md or check the troubleshooting section above.** 