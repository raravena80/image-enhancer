# Image Enhancer

A Python tool that automatically downloads images from AWS S3, enhances them using OpenAI's DALL-E API, and uploads the enhanced versions back to S3.

## Features

- **S3 Integration**: Download and upload images from/to AWS S3 buckets
- **AI-Powered Enhancement**: Uses OpenAI's DALL-E API for intelligent image enhancement
- **Flexible Authentication**: Supports multiple AWS and OpenAI authentication methods
- **Temporary File Management**: Automatic cleanup of temporary files
- **Comprehensive Logging**: Detailed logging for monitoring and debugging
- **Error Handling**: Robust error handling with meaningful error messages

## Prerequisites

- Python 3.7+
- AWS Account with S3 access
- OpenAI API account with credits
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd image-enhancer
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables (see Configuration section below).

## Configuration

### Environment Variables

Create a `.env` file in the project root directory with the following variables:

```bash
# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here

# AWS Configuration (Optional - can use IAM roles instead)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# S3 Bucket Configuration
SOURCE_BUCKET=your-source-bucket-name
DEST_BUCKET=your-destination-bucket-name
```

### AWS Authentication

The tool supports multiple AWS authentication methods:

1. **Environment Variables**: Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
2. **AWS CLI Configuration**: Use `aws configure` command
3. **IAM Roles**: For EC2 instances or Lambda functions
4. **Constructor Parameters**: Pass credentials directly to the `ImageEnhancer` class

### OpenAI API Key

You must provide an OpenAI API key either:
- As an environment variable: `OPENAI_API_KEY`
- As a parameter when initializing the `ImageEnhancer` class

## Usage

### Basic Usage

```python
from image_enhancer import ImageEnhancer

# Initialize the enhancer
enhancer = ImageEnhancer(aws_region='us-east-1')

# Process an image
enhancer.process_image(
    source_bucket='my-source-bucket',
    source_key='input-image.jpg', 
    dest_bucket='my-dest-bucket',
    dest_key='enhanced-image.jpg',
    enhancement_prompt='Make this image more vibrant and clear'
)
```

### Advanced Usage

```python
from image_enhancer import ImageEnhancer

# Initialize with explicit credentials
enhancer = ImageEnhancer(
    aws_access_key_id='your-access-key',
    aws_secret_access_key='your-secret-key',
    aws_region='us-west-2',
    openai_api_key='your-openai-key'
)

# Custom enhancement prompt
custom_prompt = "Enhance the colors, improve lighting, and increase sharpness while maintaining the original style"

enhancer.process_image(
    source_bucket='photos-input',
    source_key='vacation/beach.jpg',
    dest_bucket='photos-enhanced', 
    dest_key='vacation/beach-enhanced.jpg',
    enhancement_prompt=custom_prompt
)
```

### Running the Example

Update the configuration in the `main()` function and run:

```bash
python image-enhancer.py
```

Sample output:

```bash
INFO:__main__:Downloading image from s3://mybucket/funny.png
INFO:__main__:Image downloaded to temporary file: /var/folders/c0/y4j9mnd51yd8s3yyrd4pq7fr0000gn/T/tmpyb_yo5zq.png
INFO:__main__:Enhancing image with OpenAI...
INFO:httpx:HTTP Request: POST https://api.openai.com/v1/images/edits "HTTP/1.1 200 OK"
INFO:__main__:Image enhancement completed: /var/folders/c0/y4j9mnd51yd8s3yyrd4pq7fr0000gn/T/tmpkptwvsm9.png
INFO:__main__:Uploading processed image to s3://mybucketprocessed/enhanced_funny.png
INFO:__main__:Upload completed successfully
INFO:__main__:Successfully processed image: mybucket/funny.png -> mybucketprocessed/enhanced_funny.png
INFO:__main__:Cleaned up temporary file: /var/folders/c0/y4j9mnd51yd8s3yyrd4pq7fr0000gn/T/tmpyb_yo5zq.png
INFO:__main__:Cleaned up temporary file: /var/folders/c0/y4j9mnd51yd8s3yyrd4pq7fr0000gn/T/tmpkptwvsm9.png
Image processing completed successfully!
```

## Code Reference

### ImageEnhancer Class

#### Constructor

```python
ImageEnhancer(aws_access_key_id=None, aws_secret_access_key=None, 
              aws_region='us-east-1', openai_api_key=None)
```

**Parameters:**
- `aws_access_key_id` (str, optional): AWS access key ID
- `aws_secret_access_key` (str, optional): AWS secret access key  
- `aws_region` (str): AWS region (default: 'us-east-1')
- `openai_api_key` (str, optional): OpenAI API key

#### Methods

##### `process_image(source_bucket, source_key, dest_bucket, dest_key, enhancement_prompt)`

Complete workflow to download, enhance, and upload an image.

**Parameters:**
- `source_bucket` (str): Source S3 bucket name
- `source_key` (str): Source object key/path
- `dest_bucket` (str): Destination S3 bucket name
- `dest_key` (str): Destination object key/path
- `enhancement_prompt` (str): Description of desired enhancements

##### `download_image_from_s3(bucket_name, object_key)`

Download an image from S3 to a temporary file.

**Returns:** Path to downloaded temporary file

##### `enhance_image_with_openai(image_path, enhancement_prompt)`

Enhance an image using OpenAI's DALL-E API.

**Returns:** Path to enhanced image file

##### `upload_image_to_s3(image_path, bucket_name, object_key, content_type)`

Upload an image file to S3.

##### `cleanup_temp_files(*file_paths)`

Clean up temporary files.

## Error Handling

The tool includes comprehensive error handling for:

- AWS S3 access errors (permissions, bucket not found, etc.)
- OpenAI API errors (rate limits, invalid API key, etc.)
- File system errors (disk space, permissions, etc.)
- Network connectivity issues

All errors are logged with appropriate detail levels.

## Supported Image Formats

- **Input**: PNG, JPEG, WebP
- **Output**: PNG (default), JPEG, WebP

The tool automatically detects image formats and sets appropriate content types.

## Limitations

- **OpenAI DALL-E Limitations**: 
  - Maximum image size: 1024x1024 pixels
  - Requires OpenAI API credits
  - Subject to OpenAI's usage policies
- **S3 File Size**: Limited by AWS S3 constraints
- **Temporary Storage**: Requires sufficient local disk space for temporary files

## Cost Considerations

- **OpenAI API**: Each image enhancement consumes API credits
- **AWS S3**: Standard S3 storage and transfer costs apply
- **Data Transfer**: Consider costs for downloading/uploading large images

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use IAM roles** when running on AWS infrastructure
3. **Limit S3 bucket permissions** to required operations only
4. **Rotate API keys** regularly
5. **Use environment variables** for sensitive configuration

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../LICENSE) file for details.

## Support

For issues and questions:
1. Check the [Issues](https://github.com/raravena80/image-enhancer/issues) page
2. Review the error logs for detailed error messages
3. Ensure all prerequisites and configurations are correct

## Changelog

### v1.0.0
- Initial release
- Basic S3 download/upload functionality
- OpenAI DALL-E integration
- Comprehensive error handling and logging
