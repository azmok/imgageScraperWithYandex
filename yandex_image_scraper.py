#!/usr/bin/env python3
"""
Yandex Image Scraper
Uploads an image to Yandex, finds similar images, and downloads them all.
"""

import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urljoin, urlparse
import hashlib


def setup_driver(headless=False):
    """Setup Chrome driver with options"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    return driver


def upload_image_to_yandex(driver, image_path):
    """Upload image to Yandex and navigate to search results"""
    print(f"Opening Yandex...")
    driver.get("https://yandex.com/images/")
    
    time.sleep(2)
    
    try:
        # Click on camera icon for image search
        print("Clicking camera icon...")
        camera_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label*='camera'], button.cbir-button, .search2__button_type_camera, [class*='camera']"))
        )
        camera_button.click()
        
        time.sleep(1)
        
        # Find and use file input
        print(f"Uploading image: {image_path}")
        file_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(os.path.abspath(image_path))
        
        # Wait for upload and redirect to results
        print("Waiting for search results...")
        time.sleep(3)
        
        # Wait for image results to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".serp-item, .serp-item__link, [class*='serp-item']"))
        )
        
        print("Search results loaded!")
        return True
        
    except Exception as e:
        print(f"Error during image upload: {e}")
        return False


def click_similar_images(driver):
    """Click on 'Similar images' tab"""
    try:
        print("Looking for 'Similar images' button...")
        time.sleep(2)
        
        # Try multiple selectors for "Similar images" button
        selectors = [
            "//button[contains(text(), 'Similar')]",
            "//a[contains(text(), 'Similar')]",
            "//div[contains(text(), 'Similar')]",
            ".tabs__tab",
            "[class*='similar']",
            "a[href*='similar']"
        ]
        
        similar_button = None
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    similar_button = driver.find_element(By.XPATH, selector)
                else:
                    similar_button = driver.find_element(By.CSS_SELECTOR, selector)
                if similar_button:
                    break
            except:
                continue
        
        if similar_button:
            similar_button.click()
            print("Clicked 'Similar images' button")
            time.sleep(3)
            return True
        else:
            print("'Similar images' button not found, continuing with current results...")
            return True
            
    except Exception as e:
        print(f"Error clicking similar images: {e}")
        print("Continuing with current results...")
        return True


def scroll_and_load_images(driver, max_scrolls=50):
    """Scroll down to load more images and click 'Show more' if available"""
    print("Starting to scroll and load images...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    show_more_clicked = 0
    
    while scroll_count < max_scrolls:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Try to find and click "Show more" button
        try:
            show_more_selectors = [
                "//button[contains(text(), 'Show more')]",
                "//button[contains(text(), 'show more')]",
                ".button_theme_action",
                "[class*='show-more']",
                "[class*='load-more']"
            ]
            
            for selector in show_more_selectors:
                try:
                    if selector.startswith("//"):
                        show_more = driver.find_element(By.XPATH, selector)
                    else:
                        show_more = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if show_more.is_displayed():
                        show_more.click()
                        show_more_clicked += 1
                        print(f"Clicked 'Show more' button ({show_more_clicked} times)")
                        time.sleep(3)
                        break
                except:
                    continue
        except:
            pass
        
        # Calculate new scroll height and compare
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            print("Reached end of page or no more images to load")
            break
            
        last_height = new_height
        scroll_count += 1
        
        if scroll_count % 5 == 0:
            print(f"Scrolled {scroll_count} times...")
    
    print(f"Finished scrolling. Total scrolls: {scroll_count}, 'Show more' clicked: {show_more_clicked}")
    return True


def extract_image_urls(driver):
    """Extract all image URLs from the page"""
    print("Extracting image URLs...")
    
    image_urls = set()
    
    # Try multiple selectors for images
    selectors = [
        ".serp-item__link img",
        ".serp-item img",
        "[class*='serp-item'] img",
        ".MMImage-Origin",
        "[class*='image'] img",
        "img[src*='yandex']"
    ]
    
    for selector in selectors:
        try:
            images = driver.find_elements(By.CSS_SELECTOR, selector)
            for img in images:
                # Try different attributes for image URL
                for attr in ['src', 'data-src', 'data-bem']:
                    try:
                        url = img.get_attribute(attr)
                        if url and url.startswith('http'):
                            # Skip tiny images (thumbnails)
                            if 'thumb' not in url.lower() or 'preview' in url.lower():
                                image_urls.add(url)
                    except:
                        continue
        except Exception as e:
            continue
    
    # Also try to get original image URLs from links
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='img_url']")
        for link in links:
            href = link.get_attribute('href')
            if href and 'img_url=' in href:
                # Extract actual image URL from Yandex redirect URL
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                if 'img_url' in parsed:
                    img_url = parsed['img_url'][0]
                    image_urls.add(img_url)
    except:
        pass
    
    print(f"Found {len(image_urls)} unique image URLs")
    return list(image_urls)


def download_images(urls, output_folder):
    """Download all images to the specified folder"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    print(f"Starting download of {len(urls)} images...")
    
    successful = 0
    failed = 0
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for idx, url in enumerate(urls, 1):
        try:
            # Create filename from URL hash to avoid duplicates
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            
            # Get file extension from URL
            parsed_url = urlparse(url)
            ext = os.path.splitext(parsed_url.path)[1]
            if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                ext = '.jpg'
            
            filename = f"image_{idx:04d}_{url_hash}{ext}"
            filepath = os.path.join(output_folder, filename)
            
            # Skip if already exists
            if os.path.exists(filepath):
                print(f"[{idx}/{len(urls)}] Skipped (already exists): {filename}")
                successful += 1
                continue
            
            # Download image
            response = requests.get(url, headers=headers, timeout=10, stream=True)
            response.raise_for_status()
            
            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"[{idx}/{len(urls)}] Downloaded: {filename}")
            successful += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"[{idx}/{len(urls)}] Failed: {url[:50]}... - Error: {str(e)[:50]}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Download complete!")
    print(f"Successful: {successful}/{len(urls)}")
    print(f"Failed: {failed}/{len(urls)}")
    print(f"Output folder: {output_folder}")
    print(f"{'='*60}")


def main():
    """Main function"""
    print("="*60)
    print("Yandex Similar Image Scraper")
    print("="*60)
    
    # Get user input
    image_path = input("\nEnter the path to the image you want to search: ").strip()
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    output_folder = input("Enter the output folder for downloaded images: ").strip()
    if not output_folder:
        output_folder = "yandex_images"
        print(f"Using default folder: {output_folder}")
    
    max_scrolls = input("Enter maximum number of scrolls (default 50): ").strip()
    max_scrolls = int(max_scrolls) if max_scrolls.isdigit() else 50
    
    headless = input("Run in headless mode? (y/n, default n): ").strip().lower() == 'y'
    
    print("\n" + "="*60)
    print("Starting scraper...")
    print("="*60 + "\n")
    
    driver = None
    try:
        # Setup driver
        driver = setup_driver(headless=headless)
        
        # Upload image and search
        if not upload_image_to_yandex(driver, image_path):
            print("Failed to upload image")
            return
        
        # Click similar images
        click_similar_images(driver)
        
        # Scroll and load all images
        scroll_and_load_images(driver, max_scrolls=max_scrolls)
        
        # Extract image URLs
        image_urls = extract_image_urls(driver)
        
        if not image_urls:
            print("No images found!")
            return
        
        # Download images
        download_images(image_urls, output_folder)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            print("\nClosing browser...")
            driver.quit()
            print("Done!")


if __name__ == "__main__":
    main()
