# Temporal Image Enhancement Workflow

This project implements a distributed image enhancement system using Temporal workflows. It downloads images from S3, enhances them using OpenAI's API, and uploads the results to a different S3 bucket.

## Architecture

The system is split into several components:

- **activities.py**: Contains individual task activities (download, enhance, upload, cleanup)
- **workflows.py**: Defines the main workflow orchestrating the activities
- **worker.py**: Starts a Temporal worker to process workflows
- **run_workflow.py**: Client script to trigger workflow executions
- **.env**: Environment variables configuration

## Features

- ✅ **Fault Tolerance**: Automatic retries and error handling
- ✅ **Scalability**: Horizontal scaling with multiple workers
- ✅ **Observability**: Comprehensive logging and Temporal UI monitoring  
- ✅ **Reliability**: Guaranteed execution with Temporal's durability
- ✅ **Resource Management**: Automatic cleanup of temporary files

## Prerequisites

1. **Temporal Server**: Install and run Temporal locally or use Temporal Cloud
2. **AWS Account**: With S3 buckets and appropriate permissions
3. **OpenAI API Key**: For image enhancement (with credits)
4. **Python 3.8+**

## Installation

1. Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables by copying and editing `.env`:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

3. Start Temporal server (if running locally):
```bash
temporal server start-dev
```

## Usage

### Step 1: Start the Worker

In one terminal, start the Temporal worker:

```bash
python worker.py
```

You should see output like:
```
2024-01-15 10:30:00,123 - __main__ - INFO - Connecting to Temporal server at localhost:7233
2024-01-15 10:30:00,456 - __main__ - INFO - Using namespace: default
2024-01-15 10:30:00,789 - __main__ - INFO - Using task queue: image-enhancement-queue
2024-01-15 10:30:01,012 - __main__ - INFO - Starting worker...
2024-01-15 10:30:01,345 - __main__ - INFO - Worker is ready to process image enhancement workflows
```

### Step 2: Run a Workflow

In another terminal, trigger a workflow execution:

```bash
python run_workflow.py
```

You should see output like:
```
2024-01-15 10:31:00,123 - __main__ - INFO - Processing: s3://temporal-s3-bucket/funny.png -> s3://temporal-s3-bucket-processed/enhanced_funny.png
2024-01-15 10:31:00,456 - __main__ - INFO - Starting workflow with ID: image-enhancement-12345678-1234-1234-1234-123456789012
2024-01-15 10:31:00,789 - __main__ - INFO - Workflow started. Workflow ID: image-enhancement-12345678-1234-1234-1234-123456789012
2024-01-15 10:31:00,012 - __main__ - INFO - Waiting for workflow to complete...
2024-01-15 10:31:45,345 - __main__ - INFO - Workflow completed successfully!
2024-01-15 10:31:45,678 - __main__ - INFO - Result: Successfully processed image: s3://temporal-s3-bucket/funny.png -> s3://temporal-s3-bucket-processed/enhanced_funny.png

✅ Success: Successfully processed image:s3://temporal-s3-bucket/funny.png -> s3://temporal-s3-bucket-processed/enhanced_funny.png
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEMPORAL_ADDRESS` | Temporal server address | `localhost:7233` |
| `TEMPORAL_NAMESPACE` | Temporal namespace | `default` |
| `TEMPORAL_TASK_QUEUE` | Task queue name | `image-enhancement-queue` |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_REGION` | AWS region | `us-east-1` |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `SOURCE_BUCKET` | Source S3 bucket | `ricardotemporal` |
| `SOURCE_KEY` | Source object key | `funny.png` |
| `DEST_BUCKET` | Destination S3 bucket | `ricardotemporalprocessed` |
| `DEST_KEY` | Destination object key | `enhanced_funny.png` |
| `ENHANCEMENT_PROMPT` | Image enhancement prompt | Custom prompt |

## Monitoring

1. **Temporal Web UI**: Access at `http://localhost:8233` (if running locally)
2. **Logs**: Check worker and client logs for detailed execution information
3. **AWS CloudWatch**: Monitor S3 operations and errors

## Scaling

To scale the system:

1. **Horizontal Scaling**: Run multiple worker instances
```bash
# Terminal 1
python worker.py

# Terminal 2  
python worker.py

# Terminal 3
python worker.py
```

2. **Task Queue Partitioning**: Use different task queues for different types of work

3. **Resource Optimization**: Adjust activity timeouts and retry policies based on your needs

## Error Handling

The system includes comprehensive error handling:

- **Automatic Retries**: Failed activities are retried with exponential backoff
- **Timeout Management**: Each activity has appropriate timeouts
- **Resource Cleanup**: Temporary files are always cleaned up, even on failures
- **Detailed Logging**: All operations are logged for troubleshooting

## Troubleshooting

### Common Issues

1. **Connection Errors**: Ensure Temporal server is running
2. **AWS Permissions**: Verify S3 bucket permissions and AWS credentials
3. **OpenAI Quota**: Check OpenAI API usage and billing
4. **Timeout Issues**: Adjust activity timeouts for large images

### Debug Mode

Enable debug logging by modifying the logging level

In the .env file:

```bash
LOG_LEVEL=DEBUG
```

or in the code itself:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Production Considerations

1. **Security**: Use IAM roles instead of hardcoded AWS credentials
2. **Monitoring**: Set up proper monitoring and alerting
3. **Scaling**: Use Temporal Cloud for production workloads
4. **Cost Optimization**: Monitor OpenAI API usage and AWS costs
5. **Image Size Limits**: Consider implementing image size validation

## License

This project is licensed under the MIT License.
