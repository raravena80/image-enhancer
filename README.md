# 🎨 Image Enhancer

AI-powered image enhancement tool that downloads images from AWS S3, enhances them using OpenAI's DALL-E API, and uploads the results back to S3.

## ✨ Features

- **S3 Integration**: Seamless download/upload from AWS S3
- **AI Enhancement**: Uses OpenAI DALL-E for intelligent image improvement
- **Auto Cleanup**: Handles temporary files automatically
- **Flexible Auth**: Multiple AWS authentication options
- **Temporalized Version**: Reliable workflows under temporalized/

## 📋 Requirements

- Python 3.7+
- OpenAI API key
- AWS S3 access
- Required packages: `boto3`, `openai`, `Pillow`, `requests`, `python-dotenv`

## 🔧 General Configuration

Create a `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key  # Optional
AWS_SECRET_ACCESS_KEY=your_aws_secret   # Optional
SOURCE_BUCKET=your-source-bucket
DEST_BUCKET=your-dest-bucket
```

## 📖 Documentation

- [Original Setup Guide](SETUP.md) - Detailed installation and configuration
- [Original Code](original/image-enhancer.py) - Full original code

## 🔄 Temporalized Version (Recommended)

- See its [README.md](temporalized/README.md)

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests.

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) file for details.
