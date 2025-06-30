# Setup Guide

This guide will help you set up the Image Enhancer tool from scratch.

## 1. Prerequisites Setup

### Python Installation
Ensure you have Python 3.7 or higher installed:
```bash
python --version
```

### AWS Account Setup
1. Create an AWS account at [aws.amazon.com](https://aws.amazon.com)
2. Create S3 buckets for source and destination images
3. Set up IAM user with S3 permissions (or use IAM roles)

### OpenAI Account Setup
1. Create an account at [platform.openai.com](https://platform.openai.com)
2. Add billing information and credits
3. Generate an API key from the API Keys section

## 2. Project Setup

### Clone and Install
```bash
git clone <your-repository-url>
cd image-enhancer
pip install -r requirements.txt
```

### Environment Configuration
1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` file with your credentials:
```bash
nano .env  # or your preferred editor
```

3. Fill in the required values:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`: Your AWS credentials (optional)
   - `SOURCE_BUCKET` & `DEST_BUCKET`: Your S3 bucket names

## 3. AWS Setup Options

### Option A: Using AWS CLI (Recommended)
```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure
```

### Option B: Using Environment Variables
Set the following in your `.env` file:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

### Option C: Using IAM Roles (For EC2/Lambda)
No additional configuration needed - the tool will automatically use instance roles.

## 4. S3 Bucket Setup

### Create Buckets
```bash
# Create source bucket
aws s3 mb s3://your-source-bucket-name

# Create destination bucket
aws s3 mb s3://your-destination-bucket-name
```

### Set Permissions
Ensure your AWS user/role has the following permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::your-source-bucket-name/*",
                "arn:aws:s3:::your-destination-bucket-name/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-source-bucket-name",
                "arn:aws:s3:::your-destination-bucket-name"
            ]
        }
    ]
}
```

## 5. Testing the Setup

### Upload Test Image
```bash
# Upload a test image to your source bucket
aws s3 cp test-image.jpg s3://your-source-bucket-name/
```

### Run Test
```bash
# Modify the configuration in original.py
# Update SOURCE_BUCKET, SOURCE_KEY, DEST_BUCKET, DEST_KEY

# Run the test
python original.py
```

## 6. Troubleshooting

### Common Issues

**"No module named 'boto3'"**
```bash
pip install -r requirements.txt
```

**"Unable to locate credentials"**
- Check your `.env` file
- Run `aws configure` 
- Verify IAM permissions

**"OpenAI API key not found"**
- Check `OPENAI_API_KEY` in `.env`
- Verify the API key is valid
- Ensure you have API credits

**"Access Denied" S3 errors**
- Check bucket names are correct
- Verify IAM permissions
- Ensure buckets exist in the correct region

### Debug Mode
Enable debug logging by setting in your `.env`:
```
LOG_LEVEL=DEBUG
```

## 7. Production Deployment

### Environment Variables
For production, set environment variables directly rather than using `.env` files:

```bash
export OPENAI_API_KEY="your-key"
export AWS_ACCESS_KEY_ID="your-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

### Security Considerations
- Use IAM roles instead of access keys when possible
- Rotate API keys regularly
- Limit S3 bucket permissions to minimum required
- Never commit `.env` files to version control

### Monitoring
- Enable CloudTrail for AWS API monitoring
- Monitor OpenAI API usage and costs
- Set up CloudWatch alarms for errors

## 8. Next Steps

Once setup is complete, you can:
- Customize enhancement prompts for different use cases
- Integrate with Lambda for serverless processing
- Add batch processing capabilities
- Implement webhooks for automatic processing

For more advanced usage, see the main [README.md](README.md) file.
