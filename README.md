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

- See [SETUP.md](original/SETUP.md)

## 📖 Documentation

- [Original Setup Guide](SETUP.md) - Detailed installation and configuration
- [Original Code](original/image-enhancer.py) - Full original code

## 🔄 Temporalized Version (Recommended)

- See its [README.md](temporalized/README.md)

### ❓ Why?

#### 🤷 What Happens When It Fails?

- Processing 1,000 images overnight → Fails at #847 → Start over
- OpenAI API timeout → Manual restart required
- Network hiccup during S3 upload → Lost work
- Application crash → No recovery

#### ⚡ With Temporal

Automatic Everything:

✅ Crash recovery: Continues exactly where it left off  
✅ Smart retries: Failed API calls retry automatically  
✅ No lost work: All progress saved continuously  
✅ Scales effortlessly: Handle thousands of images concurrently  
✅ Full visibility: Real-time monitoring and debugging  

- Original version:
  - Runs 6 hours → Fails at image #847 → Start over → Manual babysitting
- Temporal version:
  - Processes 1000 successfully → Network issue → Retries automatically → Completes remaining → Zero intervention


## 🤝 Contributing

Contributions welcome! Please read general open source contribution guidelines. For example: [Kubernetes Guidelines](https://github.com/kubernetes/community/blob/master/contributors/guide/contributing.md)

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) file for details.
