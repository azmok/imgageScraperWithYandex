#!/usr/bin/env python3
"""
Yandex Reverse Image Search Scraper
With image similarity checking to ensure correct image download
"""

import os
import time
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urlparse


class YandexImageScraper:
    def __init__(self, download_folder, headless=False):
        self.download_folder = Path(download_folder)
        self.download_folder.mkdir(parents=True, exist_ok=True)
        self.downloaded_count = 0
        self.driver = None
        self.main_window = None
        self.headless = headless
        self.downloaded_urls = set()

    def setup_driver(self):
        """Setup Chrome driver with mobile emulation"""
        options = webdriver.ChromeOptions()

        # Mobile user agent (iPhone)
        mobile_emulation = {
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)

        # Chrome options
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=414,896")
        options.add_argument("--log-level=3")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(60)
        print("✓ Chrome driver initialized\n")

    def compare_images(self, img1_data, img2_data, threshold=10):
        """Compare two images using perceptual hashing"""
        try:
            from PIL import Image
            import imagehash
            from io import BytesIO

            # Load images
            img1 = Image.open(BytesIO(img1_data))
            img2 = Image.open(BytesIO(img2_data))

            # Calculate perceptual hashes
            hash1 = imagehash.average_hash(img1)
            hash2 = imagehash.average_hash(img2)

            # Calculate difference (lower = more similar)
            diff = hash1 - hash2

            return diff <= threshold

        except Exception as e:
            print(f"    ⚠ Image comparison failed: {str(e)[:40]}")
            return True  # Assume match if comparison fails

    def download_image_data(self, url):
        """Download image data without saving"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.content
        except:
            return None

    def step1_upload_image(self, image_path):
        """Step 1: Click camera icon and upload image"""
        print("=" * 60)
        print("STEP 1: Upload Query Image")
        print("=" * 60)

        try:
            # Go to Yandex Images (Image 1)
            print("→ Loading https://yandex.com/images/")
            self.driver.get("https://yandex.com/images/")
            time.sleep(3)
            self.main_window = self.driver.current_window_handle

            # Click camera icon (right icon in search bar)
            print("→ Looking for camera icon...")
            camera_selectors = [
                "button[aria-label*='camera']",
                ".search-form__camera",
                "[class*='camera']",
                "input[type='file']",
            ]

            file_input = None
            for selector in camera_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        elem = elements[0]
                        if elem.tag_name == "input":
                            file_input = elem
                            print("✓ Found file input directly")
                            break
                        else:
                            elem.click()
                            print("✓ Clicked camera icon")
                            time.sleep(2)
                            # Find file input after clicking
                            file_input = self.driver.find_element(
                                By.CSS_SELECTOR, "input[type='file']"
                            )
                            break
                except:
                    continue

            if not file_input:
                print("✗ Camera icon not found")
                return False

            # Upload image
            abs_path = str(Path(image_path).resolve())
            file_input.send_keys(abs_path)
            print(f"✓ Image uploaded: {image_path}")
            time.sleep(4)

            return True

        except Exception as e:
            print(f"✗ Error in Step 1: {e}")
            return False

    def step2_click_similar_images(self):
        """Step 2: Click 'Similar images' button (Image 2 -> Image 3)"""
        print("\n" + "=" * 60)
        print("STEP 2: Click 'Similar Images'")
        print("=" * 60)

        try:
            # Wait for results to load (Image 2)
            time.sleep(2)

            # Look for "Similar images" button
            print("→ Looking for 'Similar images' button...")
            similar_texts = [
                "Similar images",
                "similar images",
                "Похожие изображения",
                "Похожие",
            ]

            similar_button = None
            for text in similar_texts:
                try:
                    # Try by text
                    elements = self.driver.find_elements(
                        By.XPATH, f"//*[contains(text(), '{text}')]"
                    )
                    for elem in elements:
                        if elem.is_displayed():
                            similar_button = elem
                            print(f"✓ Found: '{text}'")
                            break
                    if similar_button:
                        break
                except:
                    continue

            # Try by class if not found by text
            if not similar_button:
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if btn.is_displayed() and "similar" in btn.text.lower():
                            similar_button = btn
                            break
                except:
                    pass

            if similar_button:
                similar_button.click()
                print("✓ Clicked 'Similar images' button")
                time.sleep(3)
                return True
            else:
                print("⚠ 'Similar images' button not found, continuing...")
                return True  # Continue anyway

        except Exception as e:
            print(f"✗ Error in Step 2: {e}")
            return True  # Continue anyway

    def step3_scroll_until_show_more(self, max_scrolls=50):
        """Step 3: Scroll to load images until 'Show more' appears (Image 3)"""
        print("\n" + "=" * 60)
        print("STEP 3: Scroll Until 'Show More' Button")
        print("=" * 60)

        print(f"→ Scrolling (max {max_scrolls} times)...")
        for i in range(max_scrolls):
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(2)

            # Check for "Show more" button
            try:
                show_more = self.driver.find_element(
                    By.XPATH,
                    "//*[contains(text(), 'Show more') or contains(text(), 'Показать')]",
                )
                if show_more.is_displayed():
                    print(f"✓ 'Show more' button appeared after {i+1} scrolls")
                    return True
            except:
                pass

            if (i + 1) % 10 == 0:
                print(f"  Scrolled {i+1} times...")

        print(f"→ Scrolling complete ({max_scrolls} scrolls)")
        return True

    def step4_get_thumbnails(self):
        """Step 4: Get all thumbnail elements (top-left to bottom-right order)"""
        print("\n" + "=" * 60)
        print("STEP 4: Collect All Thumbnails")
        print("=" * 60)

        # Scroll to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        print("→ Finding thumbnail elements...")
        selectors = [
            ".serp-item",
            ".SerpItem",
            "[class*='serp-item']",
            "a[href*='rpt=imageview']",
        ]

        thumbnails = []
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) > 5:
                    thumbnails = elements
                    print(f"✓ Found {len(thumbnails)} thumbnails")
                    return thumbnails
            except:
                continue

        print("⚠ Using fallback selector...")
        links = self.driver.find_elements(By.TAG_NAME, "a")
        thumbnails = [l for l in links if l.find_elements(By.TAG_NAME, "img")]
        print(f"✓ Found {len(thumbnails)} thumbnails (fallback)")
        return thumbnails

    def step5_to_10_process_thumbnail(self, thumbnail, index, total):
        """Steps 5-10: Click thumbnail -> Click download -> Verify & Save hi-res -> Close preview"""
        print("\n" + "-" * 60)
        print(f"Processing Image {index}/{total}")
        print("-" * 60)

        try:
            # Get thumbnail image URL (for initial reference)
            thumbnail_url = None
            thumbnail_data = None
            try:
                imgs = thumbnail.find_elements(By.TAG_NAME, "img")
                if imgs:
                    thumbnail_url = imgs[0].get_attribute("src")
                    if thumbnail_url and thumbnail_url.startswith("http"):
                        print(f"[{index}] → Downloading thumbnail for comparison...")
                        thumbnail_data = self.download_image_data(thumbnail_url)
                        if thumbnail_data:
                            print(f"[{index}] ✓ Thumbnail data ready for comparison")
            except:
                pass

            # STEP 5: Click thumbnail to open preview (Image 4)
            print(f"[{index}] Step 5: Clicking thumbnail...")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", thumbnail
            )
            time.sleep(0.5)

            try:
                thumbnail.click()
            except:
                self.driver.execute_script("arguments[0].click();", thumbnail)

            time.sleep(2)
            print(f"[{index}] ✓ Preview opened")

            # Get PREVIEW image (this is the fallback image)
            preview_url = None
            preview_data = None
            print(f"[{index}] → Collecting preview image...")

            try:
                # Look for large preview images in the modal
                preview_selectors = [
                    "img.MMImage-Origin",
                    "img.MMImage-Preview",
                    "img[class*='Origin']",
                    "img[class*='Preview']",
                    "img[class*='Modal']",
                    ".Modal img",
                    ".MMModal img",
                ]

                preview_imgs = []
                for selector in preview_selectors:
                    try:
                        imgs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for img in imgs:
                            if img.is_displayed():
                                preview_imgs.append(img)
                    except:
                        continue

                # If no specific preview selector worked, get all visible images
                if not preview_imgs:
                    all_imgs = self.driver.find_elements(By.TAG_NAME, "img")
                    preview_imgs = [img for img in all_imgs if img.is_displayed()]

                # Find largest preview image (usually the main preview)
                if preview_imgs:
                    largest_preview = max(
                        preview_imgs,
                        key=lambda img: img.size["width"] * img.size["height"],
                    )
                    preview_url = largest_preview.get_attribute("src")

                    if (
                        preview_url
                        and preview_url.startswith("http")
                        and preview_url != thumbnail_url
                    ):
                        print(f"[{index}] → Downloading preview image...")
                        preview_data = self.download_image_data(preview_url)
                        if preview_data:
                            print(f"[{index}] ✓ Preview image ready (fallback)")
                        else:
                            print(f"[{index}] ⚠ Preview image download failed")
                    else:
                        print(f"[{index}] ⚠ Preview URL same as thumbnail or invalid")
            except Exception as e:
                print(f"[{index}] ⚠ Could not get preview image: {str(e)[:40]}")

            # If preview failed, keep thumbnail as ultimate fallback
            if not preview_data and thumbnail_data:
                print(f"[{index}] → Using thumbnail as ultimate fallback")
                preview_data = thumbnail_data
                preview_url = thumbnail_url

            # STEP 6: Click download button (Image 5 - red circle)
            print(f"[{index}] Step 6: Looking for download button...")
            download_button = None

            # Try multiple selectors for download button
            download_selectors = [
                "a[download]",
                "button[download]",
                "a[href][class*='Button']",
                ".MMButton",
                "a[class*='button']",
                "a[target='_blank']",
            ]

            for selector in download_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        if btn.is_displayed():
                            # Check if it's likely a download button
                            aria_label = btn.get_attribute("aria-label") or ""
                            class_name = btn.get_attribute("class") or ""

                            if (
                                "download" in aria_label.lower()
                                or "download" in class_name.lower()
                            ):
                                download_button = btn
                                break
                            # Also check for buttons that open new window
                            if btn.get_attribute("target") == "_blank":
                                download_button = btn
                                break

                    if download_button:
                        print(f"[{index}] ✓ Found download button: {selector}")
                        break
                except:
                    continue

            # STEP 7: Click download -> New window opens with hi-res (Image 6)
            success = False

            if download_button:
                try:
                    print(f"[{index}] Step 7: Clicking download button...")
                    original_windows = set(self.driver.window_handles)

                    # Click download button
                    try:
                        download_button.click()
                    except:
                        self.driver.execute_script(
                            "arguments[0].click();", download_button
                        )

                    time.sleep(3)

                    # Check if new window opened
                    new_windows = set(self.driver.window_handles) - original_windows

                    if new_windows:
                        # Switch to new window (Image 6)
                        new_window = list(new_windows)[0]
                        self.driver.switch_to.window(new_window)
                        print(f"[{index}] ✓ New window opened")
                        time.sleep(2)

                        # Collect ALL image URLs from new window
                        print(f"[{index}] → Collecting all images in new window...")
                        candidate_urls = []

                        # Method 1: Check if current URL is direct image
                        current_url = self.driver.current_url
                        if any(
                            ext in current_url.lower()
                            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
                        ):
                            candidate_urls.append(current_url)
                            print(f"[{index}]   • Direct URL: {current_url[:60]}...")

                        # Method 2: Find all <img> tags
                        try:
                            img_elements = self.driver.find_elements(By.TAG_NAME, "img")
                            for img in img_elements:
                                try:
                                    if img.is_displayed():
                                        src = img.get_attribute("src")
                                        if (
                                            src
                                            and src.startswith("http")
                                            and "data:" not in src
                                        ):
                                            if any(
                                                ext in src.lower()
                                                for ext in [
                                                    ".jpg",
                                                    ".jpeg",
                                                    ".png",
                                                    ".gif",
                                                    ".webp",
                                                ]
                                            ):
                                                if src not in candidate_urls:
                                                    candidate_urls.append(src)
                                except:
                                    continue
                            print(f"[{index}]   • Found {len(img_elements)} <img> tags")
                        except:
                            pass

                        # Method 3: Find all <a> tags with image links
                        try:
                            link_elements = self.driver.find_elements(By.TAG_NAME, "a")
                            for link in link_elements:
                                try:
                                    href = link.get_attribute("href")
                                    if href and href.startswith("http"):
                                        if any(
                                            ext in href.lower()
                                            for ext in [
                                                ".jpg",
                                                ".jpeg",
                                                ".png",
                                                ".gif",
                                                ".webp",
                                            ]
                                        ):
                                            if href not in candidate_urls:
                                                candidate_urls.append(href)
                                except:
                                    continue
                            print(f"[{index}]   • Found {len(link_elements)} <a> tags")
                        except:
                            pass

                        print(
                            f"[{index}] ✓ Total candidates: {len(candidate_urls)} images"
                        )

                        # Download and compare each candidate
                        best_match = None
                        best_match_url = None
                        best_match_diff = 999999

                        if thumbnail_data and candidate_urls:
                            print(f"[{index}] → Comparing candidates with thumbnail...")

                            for i, url in enumerate(candidate_urls, 1):
                                try:
                                    # Download candidate image
                                    candidate_data = self.download_image_data(url)

                                    if candidate_data:
                                        # Compare with thumbnail
                                        from PIL import Image
                                        import imagehash
                                        from io import BytesIO

                                        try:
                                            img_thumb = Image.open(
                                                BytesIO(thumbnail_data)
                                            )
                                            img_candidate = Image.open(
                                                BytesIO(candidate_data)
                                            )

                                            hash_thumb = imagehash.average_hash(
                                                img_thumb
                                            )
                                            hash_candidate = imagehash.average_hash(
                                                img_candidate
                                            )

                                            diff = hash_thumb - hash_candidate

                                            print(
                                                f"[{index}]     [{i}/{len(candidate_urls)}] Diff: {diff} - {url[:50]}..."
                                            )

                                            # Track best match
                                            if diff < best_match_diff:
                                                best_match_diff = diff
                                                best_match = candidate_data
                                                best_match_url = url

                                        except:
                                            pass

                                except Exception as e:
                                    continue

                            # Evaluate best match
                            if best_match and best_match_diff <= 15:  # threshold
                                print(
                                    f"[{index}] ✓ Best match found! Diff: {best_match_diff}"
                                )
                                print(f"[{index}] ✓ URL: {best_match_url[:70]}...")
                                if self.save_image(best_match_url, best_match, index):
                                    success = True
                            else:
                                if best_match:
                                    print(
                                        f"[{index}] ⚠ Best match diff too high: {best_match_diff}"
                                    )
                                else:
                                    print(f"[{index}] ⚠ No matching image found")
                                print(f"[{index}] → Using thumbnail fallback")

                        elif candidate_urls and not thumbnail_data:
                            # No thumbnail to compare, use largest image
                            print(
                                f"[{index}] → No thumbnail for comparison, using largest image..."
                            )

                            largest_size = 0
                            largest_url = None
                            largest_data = None

                            for url in candidate_urls:
                                try:
                                    data = self.download_image_data(url)
                                    if data:
                                        from PIL import Image
                                        from io import BytesIO

                                        img = Image.open(BytesIO(data))
                                        size = img.width * img.height

                                        if size > largest_size:
                                            largest_size = size
                                            largest_url = url
                                            largest_data = data
                                except:
                                    continue

                            if largest_data:
                                print(
                                    f"[{index}] ✓ Largest image: {largest_size} pixels"
                                )
                                if self.save_image(largest_url, largest_data, index):
                                    success = True

                        # STEP 8: Close new window
                        print(f"[{index}] Step 8: Closing new window...")
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        print(f"[{index}] ✓ Returned to main window")

                    else:
                        print(f"[{index}] ⚠ New window didn't open")

                except Exception as e:
                    print(f"[{index}] ✗ Error with download button: {str(e)[:50]}")
                    # Make sure we're back to main window
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                    except:
                        pass

            # STEP 7 Fallback: Use preview image if hi-res not found or failed
            if not success:
                print(f"[{index}] → Using preview image fallback...")
                if (
                    preview_url
                    and preview_data
                    and preview_url not in self.downloaded_urls
                ):
                    if self.save_image(preview_url, preview_data, index):
                        success = True
                        print(f"[{index}] ✓ Saved preview image")
                elif (
                    thumbnail_url
                    and thumbnail_data
                    and thumbnail_url not in self.downloaded_urls
                ):
                    # Ultimate fallback: thumbnail
                    print(f"[{index}] → Using thumbnail as ultimate fallback...")
                    if self.save_image(thumbnail_url, thumbnail_data, index):
                        success = True
                        print(f"[{index}] ✓ Saved thumbnail image")

            # STEP 8: Close preview panel (click X button)
            print(f"[{index}] Step 8: Closing preview panel...")
            time.sleep(0.5)

            # Try ESC key first
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(0.5)
                print(f"[{index}] ✓ Closed with ESC")
            except:
                pass

            # Try clicking X (close) button
            try:
                close_selectors = [
                    "button[aria-label*='close']",
                    "button[aria-label*='Close']",
                    "[class*='close']",
                    "[class*='Close']",
                ]

                for selector in close_selectors:
                    try:
                        close_btns = self.driver.find_elements(
                            By.CSS_SELECTOR, selector
                        )
                        for btn in close_btns:
                            if (
                                btn.is_displayed() and btn.size["width"] < 100
                            ):  # X button is usually small
                                btn.click()
                                print(f"[{index}] ✓ Clicked X button")
                                time.sleep(0.5)
                                return True
                    except:
                        continue
            except:
                pass

            return True

        except Exception as e:
            print(f"[{index}] ✗ Error: {str(e)[:60]}")
            # Recovery: close any extra windows and preview
            try:
                while len(self.driver.window_handles) > 1:
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    self.driver.close()
                self.driver.switch_to.window(self.main_window)
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except:
                pass
            return False

    def save_image(self, url, image_data, index):
        """Save image data to file"""
        try:
            # Skip duplicates
            if url in self.downloaded_urls:
                print(f"[{index}] ⊘ Skipped (duplicate)")
                return False

            # Save
            ext = Path(urlparse(url).path).suffix or ".jpg"
            if not ext or ext == ".":
                ext = ".jpg"
            filename = f"yandex_{index:04d}{ext}"
            filepath = self.download_folder / filename

            with open(filepath, "wb") as f:
                f.write(image_data)

            self.downloaded_urls.add(url)
            self.downloaded_count += 1

            print(f"[{index}] ✓ Saved: {filename}")
            return True

        except Exception as e:
            print(f"[{index}] ✗ Save failed: {str(e)[:40]}")
            return False

    def scrape(self, query_image_path, max_scrolls=50):
        """Main scraping workflow following exact steps 1-10"""
        try:
            print("\n" + "=" * 60)
            print("YANDEX IMAGE SCRAPER - STARTING")
            print("=" * 60 + "\n")

            self.setup_driver()

            # STEP 1: Upload image
            if not self.step1_upload_image(query_image_path):
                print("\n✗ Failed at Step 1")
                return

            # STEP 2: Click "Similar images"
            self.step2_click_similar_images()

            # STEP 3: Scroll until "Show more"
            self.step3_scroll_until_show_more(max_scrolls)

            # STEP 4: Get all thumbnails
            thumbnails = self.step4_get_thumbnails()

            if not thumbnails:
                print("\n✗ No thumbnails found")
                return

            # STEPS 5-10: Process each thumbnail
            print("\n" + "=" * 60)
            print(f"STEPS 5-10: Processing {len(thumbnails)} Images")
            print("=" * 60)

            for i, thumbnail in enumerate(thumbnails, 1):
                self.step5_to_10_process_thumbnail(thumbnail, i, len(thumbnails))
                time.sleep(1)  # Delay between images

            # Summary
            print("\n" + "=" * 60)
            print("SCRAPING COMPLETE!")
            print("=" * 60)
            print(
                f"✓ Successfully downloaded: {self.downloaded_count}/{len(thumbnails)} images"
            )
            print(f"✓ Saved to: {self.download_folder.resolve()}")
            print("=" * 60 + "\n")

        finally:
            if self.driver:
                self.driver.quit()
                print("✓ Browser closed\n")


def main():
    """Main function"""
    print("=" * 60)
    print("Yandex Reverse Image Search Scraper")
    print("With Image Similarity Verification")
    print("=" * 60)

    # Get input
    query_image = input("\nEnter query image path: ").strip().strip("\"'")

    if not os.path.exists(query_image):
        print(f"✗ Error: File not found: {query_image}")
        return

    output_folder = (
        input("Enter output folder (default: yandex_images): ").strip()
        or "yandex_images"
    )

    max_scrolls_input = input("Enter max scrolls (default: 30): ").strip()
    max_scrolls = int(max_scrolls_input) if max_scrolls_input else 30

    headless_input = input("Run in headless mode? (y/n, default: n): ").strip().lower()
    headless = headless_input == "y"

    # Run scraper
    scraper = YandexImageScraper(output_folder, headless=headless)
    scraper.scrape(query_image, max_scrolls)


if __name__ == "__main__":
    main()
