# Yandex Similar Image Scraper

A Python script that uploads an image to Yandex Images, finds similar images, and downloads them all automatically.

## Features

- Upload an image to Yandex Image Search
- Navigate to "Similar Images" results
- Automatically scroll and load more images
- Click "Show more" button when it appears
- Download all loaded images to a specified folder
- Avoid duplicate downloads
- Progress tracking and statistics

## Prerequisites

1. **Python 3.7+** installed on your system

2. **Google Chrome** browser installed

3. **ChromeDriver** matching your Chrome version
   - Download from: https://chromedriver.chromium.org/downloads
   - Or install via package manager:
     - Windows (with Chocolatey): `choco install chromedriver`
     - macOS (with Homebrew): `brew install chromedriver`
     - Linux: `sudo apt-get install chromium-chromedriver`

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install selenium requests urllib3
```

3. Make sure ChromeDriver is in your PATH, or place it in the same directory as the script

## Usage

Run the script:
```bash
python yandex_image_scraper.py
```

The script will prompt you for:

1. **Image path**: Path to the image you want to search (e.g., `/path/to/image.jpg`)
2. **Output folder**: Where to save downloaded images (e.g., `my_images`)
3. **Max scrolls**: Maximum number of times to scroll (default: 50)
4. **Headless mode**: Run without showing browser window (y/n)

### Example

```
Enter the path to the image you want to search: /home/user/sample.jpg
Enter the output folder for downloaded images: downloaded_images
Enter maximum number of scrolls (default 50): 30
Run in headless mode? (y/n, default n): n
```

## How It Works

1. **Opens Yandex Images** and clicks the camera icon for reverse image search
2. **Uploads your image** using the file input
3. **Waits for search results** to load
4. **Clicks "Similar Images"** tab if available
5. **Scrolls down repeatedly** to load more images
6. **Clicks "Show more"** button when it appears
7. **Extracts all image URLs** from the loaded page
8. **Downloads images** to your specified folder with unique filenames

## Features & Options

### Automatic Scrolling
- The script automatically scrolls to the bottom of the page
- Waits for new images to load after each scroll
- Stops when no more images are loading or max scrolls reached

### "Show More" Button Handling
- Automatically detects and clicks the "Show more" button
- Continues scrolling after clicking
- Tracks how many times the button was clicked

### Download Management
- Creates output folder if it doesn't exist
- Generates unique filenames using URL hash
- Skips already downloaded images (resume support)
- Shows download progress and statistics

### Error Handling
- Handles network errors gracefully
- Continues downloading even if some images fail
- Provides detailed error messages
- Shows final success/failure statistics

## Troubleshooting

### ChromeDriver version mismatch
```
Error: This version of ChromeDriver only supports Chrome version XX
```
**Solution**: Download ChromeDriver matching your Chrome version from https://chromedriver.chromium.org/

### Selenium not found
```
ModuleNotFoundError: No module named 'selenium'
```
**Solution**: Install dependencies with `pip install -r requirements.txt`

### Upload button not found
**Solution**: Yandex may have changed their UI. The script uses multiple selectors to find elements, but you may need to update the selectors in the code.

### No images downloaded
**Possible causes**:
- Yandex blocked the request (try adding delays or using headless=False)
- Image URLs are behind authentication
- Network connectivity issues

**Solution**: Run in non-headless mode to see what's happening, and check the console output for errors.

### Rate limiting
If downloads are failing, Yandex might be rate-limiting. The script includes small delays between downloads, but you can increase them by modifying the `time.sleep()` value in the `download_images()` function.

## Customization

### Change User Agent
Modify the `User-Agent` string in `setup_driver()` and `download_images()` functions.

### Adjust Scroll Speed
Change `time.sleep(2)` in `scroll_and_load_images()` to increase/decrease wait time between scrolls.

### Modify Download Delay
Change `time.sleep(0.1)` in `download_images()` to adjust delay between downloads.

### Add More Selectors
If the script can't find elements, add more CSS selectors or XPath expressions to the selector lists.

## Limitations

- Depends on Yandex's current HTML structure
- May need updates if Yandex changes their website
- Download speed limited to avoid overwhelming servers
- Some images may be behind CDN protection

## Legal Notice

This script is for educational purposes only. Always respect:
- Website terms of service
- Copyright and intellectual property rights
- Rate limiting and responsible scraping practices
- Personal data and privacy regulations

Use responsibly and at your own risk.

## License

MIT License - feel free to modify and use as needed.
