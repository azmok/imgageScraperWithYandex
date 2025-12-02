# All files is created mainly with Claude.ai and Gemini collaboration and sometimes modify with me.


# Yandex Image Scraper - Local PC Version

Standalone Python script for scraping images from Yandex reverse image search.

## Requirements

- Python 3.7+
- Google Chrome browser installed
- Internet connection

## Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements_local.txt
```

This installs:
- `selenium` - Browser automation
- `webdriver-manager` - Automatic ChromeDriver management
- `requests` - HTTP requests for downloading images

2. **Install Google Chrome:**
   - Download from: https://www.google.com/chrome/
   - The script will automatically download the matching ChromeDriver

## Usage

### Interactive Mode (Recommended)

Simply run the script and follow the prompts:

```bash
python yandex_scraper_local.py
```

You'll be asked for:
1. **Query image path** - Path to the image you want to search
2. **Output folder** - Where to save downloaded images (default: `yandex_images`)
3. **Max scrolls** - Maximum number of scrolls (default: 30)
4. **Headless mode** - Run without showing browser (y/n, default: n)

### Example Session

```
$ python yandex_scraper_local.py

============================================================
Yandex Reverse Image Search Scraper
============================================================

Enter the path to your query image: C:\Users\Me\Pictures\query.jpg
Enter output folder (default: yandex_images): downloaded_images
Enter max scrolls (default: 30): 20
Run in headless mode? (y/n, default: n): n

⚙️  Configuration:
   Query image: C:\Users\Me\Pictures\query.jpg
   Output folder: downloaded_images
   Max scrolls: 20
   Headless: False

============================================================
🚀 Starting Yandex Image Scraper
============================================================
✓ Chrome driver initialized

🔍 Uploading image: C:\Users\Me\Pictures\query.jpg
  → Loading Yandex Images...
  → Page loaded, searching for camera button...
  ✓ Found camera button with: button[class*='camera']
  ✓ Clicked camera button
  ✓ Image uploaded: C:\Users\Me\Pictures\query.jpg
  → Waiting for search results...
  ✓ Found 45 results with: .serp-item
  ✓ Clicked 'Similar' button

📜 Scrolling to load more images...
  ✓ Found 'Show more' after 8 scrolls

📸 Collecting thumbnails...
  ✓ Found 120 thumbnails

============================================================
⬇️  Downloading 120 images...
============================================================

  ✓ [1] yandex_0001.jpg
  ✓ [2] yandex_0002.png
  ...

============================================================
✅ Download Complete!
   Successfully downloaded: 115/120
   Saved to: C:\Users\Me\downloaded_images
============================================================

✓ Browser closed
```

## Features

### Headless vs Normal Mode

**Normal Mode (default):**
- Shows browser window
- You can see what the scraper is doing
- Good for debugging
- Slower but visual feedback

**Headless Mode:**
- No browser window
- Runs in background
- Faster
- Good for automation

### Automatic ChromeDriver

The script uses `webdriver-manager` which:
- Automatically downloads the correct ChromeDriver version
- Matches your Chrome browser version
- No manual setup needed

### Mobile User Agent

The script emulates an iPhone to get the mobile version of Yandex, which is more reliable for scraping.

## File Structure

After running, you'll have:
```
your-folder/
├── yandex_scraper_local.py    # Main script
├── requirements_local.txt      # Dependencies
└── yandex_images/              # Downloaded images (default)
    ├── yandex_0001.jpg
    ├── yandex_0002.png
    ├── yandex_0003.jpg
    └── ...
```

## Programmatic Usage

You can also import and use the scraper in your own code:

```python
from yandex_scraper_local import YandexImageScraper

# Create scraper
scraper = YandexImageScraper(
    download_folder="my_images",
    headless=True  # Run without showing browser
)

# Run scraping
scraper.scrape(
    query_image_path="path/to/image.jpg",
    max_scrolls=50
)
```

## Troubleshooting

### Chrome/ChromeDriver Issues

If you get ChromeDriver errors:
1. Make sure Chrome is installed
2. Try updating Chrome to the latest version
3. Delete the webdriver-manager cache:
   - Windows: `C:\Users\YourName\.wdm\`
   - Mac/Linux: `~/.wdm/`

### "File not found" Error

Make sure to provide the full path to your image:
- Windows: `C:\Users\Me\Pictures\image.jpg`
- Mac/Linux: `/Users/me/Pictures/image.jpg`
- Or use relative path: `./images/image.jpg`

### No Images Downloaded

- Check your internet connection
- Try increasing `max_scrolls`
- Run in normal mode (not headless) to see what's happening
- Yandex might have changed their page structure

### Slow Performance

- Use headless mode for faster execution
- Reduce `max_scrolls` to get fewer images
- Check your internet speed

## Advanced Configuration

Edit the script to customize:

**Change wait times:**
```python
time.sleep(5)  # Line 67 - After page load
time.sleep(2)  # Line 282 - Between downloads
```

**Change user agent:**
```python
mobile_emulation = {
    "userAgent": "Your custom user agent here"
}
```

**Change download timeout:**
```python
response = requests.get(url, headers=headers, timeout=15)  # Line 221
```

## Limitations

- Only downloads what's loaded after scrolling
- Some sources may be dead/unavailable
- Rate limiting may apply for excessive use
- Yandex may update their page structure

## Tips

1. **For best results:**
   - Use clear, high-quality query images
   - Start with fewer scrolls (10-20) to test
   - Use normal mode first to see the process

2. **For large batches:**
   - Use headless mode
   - Increase max_scrolls (50-100)
   - Add delay between images if needed

3. **File organization:**
   - Use descriptive folder names
   - Sort images by query image used
   - Clean up thumbnails vs high-res images

## License

MIT License - Free to use and modify

## Support

If you encounter issues:
1. Check Chrome is up to date
2. Run in normal mode to see the browser
3. Check the console output for error messages
4. Make sure the query image path is correct
