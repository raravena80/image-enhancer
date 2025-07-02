# Temporal Image Enhancement Workflow

This project implements a distributed image enhancement system using Temporal workflows. It downloads images from S3, enhances them using OpenAI's API, and uploads the results to a different S3 bucket with support for batch processing of multiple images concurrently.

## Architecture

The system is split into several components:

- **activities.py**: Contains individual task activities (download, enhance, upload, cleanup)
- **workflows.py**: Defines the main workflow orchestrating the activities
- **worker.py**: Starts a Temporal worker to process workflows
- **run_workflow.py**: Client script to trigger workflow executions with batch processing support
- **.env**: Environment variables configuration

## Features

- ✅ **Fault Tolerance**: Automatic retries and error handling
- ✅ **Scalability**: Horizontal scaling with multiple workers
- ✅ **Batch Processing**: Process multiple images concurrently with configurable limits
- ✅ **Flexible Configuration**: Support both JSON and simple comma-separated image lists
- ✅ **Observability**: Comprehensive logging and Temporal UI monitoring  
- ✅ **Reliability**: Guaranteed execution with Temporal's durability
- ✅ **Resource Management**: Automatic cleanup of temporary files
- ✅ **Performance Monitoring**: Detailed timing and success/failure tracking

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

### Step 2: Configure Images for Processing

You can process images in several ways:

#### Single Image (Legacy Mode)
Set individual environment variables:
```bash
SOURCE_BUCKET=my-source-bucket
SOURCE_KEY=image.jpg
DEST_BUCKET=my-dest-bucket
DEST_KEY=enhanced_image.jpg
```

#### Multiple Images - Simple Format
Use comma-separated list (uses default buckets):
```bash
IMAGES_TO_PROCESS=image1.jpg,image2.png,folder/image3.jpeg
```

#### Multiple Images - JSON Format
For maximum flexibility with different buckets:
```bash
IMAGES_TO_PROCESS='[
  {
    "source_bucket": "bucket1",
    "source_key": "image1.jpg",
    "dest_bucket": "processed-bucket1",
    "dest_key": "enhanced_image1.jpg"
  },
  {
    "source_bucket": "bucket2",
    "source_key": "photos/vacation.png",
    "dest_bucket": "processed-bucket2",
    "dest_key": "photos/enhanced_vacation.png"
  }
]'
```

### Step 3: Configure Batch Processing

Set concurrency limits and processing options:
```bash
# Maximum number of concurrent workflows (default: 5)
MAX_CONCURRENT_WORKFLOWS=10

# Custom enhancement prompt
ENHANCEMENT_PROMPT="Make this image more vibrant, increase clarity and sharpness, improve lighting"
```

### Step 4: Run the Workflow

In another terminal, trigger workflow execution:

```bash
python run_workflow.py
```

You should see output like:
```
2024-01-15 10:31:00,123 - __main__ - INFO - Processing 3 images with max concurrency: 5
2024-01-15 10:31:00,456 - __main__ - INFO - Starting all workflows...
2024-01-15 10:31:00,789 - __main__ - INFO - Starting workflow for: s3://bucket1/image1.jpg
2024-01-15 10:31:01,012 - __main__ - INFO - Starting workflow for: s3://bucket1/image2.png
2024-01-15 10:31:01,345 - __main__ - INFO - Starting workflow for: s3://bucket1/image3.jpeg
2024-01-15 10:31:45,678 - __main__ - INFO - ✅ s3://bucket1/image1.jpg -> s3://processed/enhanced_image1.jpg (12.3s)
2024-01-15 10:31:47,901 - __main__ - INFO - ✅ s3://bucket1/image2.png -> s3://processed/enhanced_image2.png (13.1s)
2024-01-15 10:31:50,234 - __main__ - INFO - ✅ s3://bucket1/image3.jpeg -> s3://processed/enhanced_image3.jpeg (14.2s)

================================================================================
BATCH PROCESSING SUMMARY
================================================================================
Total images: 3
Successful: 3
Failed: 0
Total duration: 15.8s
Average per image: 5.3s
================================================================================

🎉 All 3 images processed successfully!
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
| `SOURCE_BUCKET` | Default source S3 bucket | `source-bucket` |
| `SOURCE_KEY` | Source object key (single image mode) | `image.png` |
| `DEST_BUCKET` | Default destination S3 bucket | `dest-bucket` |
| `DEST_KEY` | Destination object key (single image mode) | `enhanced_image.png` |
| `IMAGES_TO_PROCESS` | Batch image configuration (JSON or CSV) | None |
| `MAX_CONCURRENT_WORKFLOWS` | Maximum concurrent workflows | `5` |
| `ENHANCEMENT_PROMPT` | Image enhancement prompt | Custom prompt |
| `LOG_LEVEL` | Logging level | `INFO` |

### Batch Processing Configuration

#### Simple Format
When using the simple comma-separated format, the system automatically:
- Uses `SOURCE_BUCKET` and `DEST_BUCKET` as defaults
- Adds `enhanced_` prefix to destination filenames
- Preserves folder structure in destination keys

Example:
```bash
SOURCE_BUCKET=my-images
DEST_BUCKET=my-processed-images
IMAGES_TO_PROCESS=photo1.jpg,vacation/photo2.png,events/photo3.jpeg
```

Results in:
- `my-images/photo1.jpg` → `my-processed-images/enhanced_photo1.jpg`
- `my-images/vacation/photo2.png` → `my-processed-images/vacation/enhanced_photo2.png`
- `my-images/events/photo3.jpeg` → `my-processed-images/events/enhanced_photo3.jpeg`

#### JSON Format
For maximum control, use JSON format to specify different buckets and custom destination names:

```bash
IMAGES_TO_PROCESS='[
  {"source_bucket": "raw-photos", "source_key": "IMG001.jpg", "dest_bucket": "enhanced-photos", "dest_key": "portfolio/enhanced_IMG001.jpg"},
  {"source_bucket": "raw-photos", "source_key": "IMG002.png", "dest_bucket": "enhanced-photos", "dest_key": "portfolio/enhanced_IMG002.png"}
]'
```

### Performance Tuning

#### Concurrency Settings

- **Low concurrency (1-3)**: Better for resource-constrained environments or API rate limits
- **Medium concurrency (5-10)**: Good balance for most use cases
- **High concurrency (10+)**: Maximum performance with sufficient resources

#### Considerations

- **OpenAI API Rate Limits**: Monitor your OpenAI usage to avoid hitting rate limits
- **AWS S3 Limits**: S3 can handle high concurrency, but monitor costs
- **Worker Resources**: Ensure your Temporal workers have sufficient resources
- **Network Bandwidth**: Higher concurrency requires more bandwidth

## Monitoring

1. **Temporal Web UI**: Access at `http://localhost:8233` (if running locally)
2. **Batch Processing Logs**: Detailed per-image and summary statistics
3. **Real-time Progress**: See workflows starting and completing in real-time
4. **Performance Metrics**: Duration tracking per image and overall batch
5. **AWS CloudWatch**: Monitor S3 operations and errors

## Error Handling

- **Automatic Retries**: Failed activities are retried with exponential backoff
- **Timeout Management**: Each activity has appropriate timeouts
- **Resource Cleanup**: Temporary files are always cleaned up, even on failures
- **Detailed Logging**: All operations are logged for troubleshooting
- **Partial Failure Handling**: Batch processing continues even if individual images fail
- **Exception Isolation**: One failed image doesn't affect others in the batch

## Troubleshooting

### Common Issues

1. **Connection Errors**: Ensure Temporal server is running
2. **AWS Permissions**: Verify S3 bucket permissions and AWS credentials
3. **OpenAI Quota**: Check OpenAI API usage and billing
4. **Timeout Issues**: Adjust activity timeouts for large images
5. **Rate Limiting**: Reduce `MAX_CONCURRENT_WORKFLOWS` if hitting API limits
6. **Memory Issues**: Lower concurrency if running out of memory

### Debug Mode

Enable debug logging by modifying the logging level in the .env file:

```bash
LOG_LEVEL=DEBUG
```

### Batch Processing Debug

To debug batch processing issues:

1. **Start with low concurrency**: Set `MAX_CONCURRENT_WORKFLOWS=1`
2. **Test with single image**: Use simple format with one image
3. **Check JSON format**: Validate JSON syntax if using complex configuration
4. **Monitor Temporal UI**: Check workflow executions in real-time

## Production Considerations

1. **Security**: Use IAM roles instead of hardcoded AWS credentials
2. **Monitoring**: Set up proper monitoring and alerting for batch jobs
3. **Scaling**: Use Temporal Cloud for production workloads
4. **Cost Optimization**: Monitor OpenAI API usage and AWS costs
5. **Image Size Limits**: Consider implementing image size validation
6. **Batch Size Management**: Avoid processing too many images simultaneously
7. **Resource Planning**: Scale workers based on expected batch sizes

## Performance Examples

### Single Image Processing
```bash
# Process one image
SOURCE_BUCKET=my-bucket
SOURCE_KEY=photo.jpg
DEST_BUCKET=processed-bucket
DEST_KEY=enhanced_photo.jpg
MAX_CONCURRENT_WORKFLOWS=1
```

### Small Batch (5 images)
```bash
# Process 5 images with moderate concurrency
IMAGES_TO_PROCESS=img1.jpg,img2.jpg,img3.jpg,img4.jpg,img5.jpg
MAX_CONCURRENT_WORKFLOWS=3
```

### Large Batch (50+ images)
```bash
# Process many images with higher concurrency
IMAGES_TO_PROCESS=folder1/*.jpg,folder2/*.png
MAX_CONCURRENT_WORKFLOWS=10
```

## Scaling Strategies

### Horizontal Scaling
Run multiple worker instances to handle larger batches:

```bash
# Terminal 1
python worker.py

# Terminal 2  
python worker.py

# Terminal 3
python worker.py
```

### Batch Partitioning
For very large image sets, consider splitting into smaller batches:

```bash
# Process first batch
IMAGES_TO_PROCESS=batch1/image1.jpg,batch1/image2.jpg
python run_workflow.py

# Process second batch
IMAGES_TO_PROCESS=batch2/image1.jpg,batch2/image2.jpg
python run_workflow.py
```

## License

This project is licensed under Apache 2.0 License.
