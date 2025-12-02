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
        """Setup Chrome driver in Desktop Mode"""
        options = webdriver.ChromeOptions()

        # Use a standard Desktop User Agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Chrome options
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-popup-blocking")

        # IMPORTANT: Set a large window size to ensure the Sidebar Preview opens
        # If the window is too narrow, Yandex might force a mobile-style layout
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")

        # Remove the 'enable-automation' banner to be stealthier
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(60)
        print("✓ Chrome driver initialized (Desktop Mode)\n")

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
            time.sleep(2)
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
        print("STEP 2:::::Start::::: Click 'Similar Images'")
        print("=" * 60)

        try:
            # Wait for results to load (Image 2)
            time.sleep(3)

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
                print("STEP 2:::::End::::: Click 'Similar Images'")

                time.sleep(3)

                return True
            else:
                print("⚠ 'Similar images' button not found, continuing...")
                return True  # Continue anyway

        except Exception as e:
            print(f"✗ Error in Step 2: {e}")
            return True  # Continue anyway

    def step3_scroll_until_show_more(self, max_scrolls=50):
        """Step 3: Scroll until page height stops increasing"""
        print("\n" + "=" * 60)
        # print("STEP 3::::Start:::: Infinite Scroll (Height Check)")
        # time.sleep(10)
        print("=" * 60)
        print(f"→ Scrolling (max {max_scrolls} steps)...")

        # 1. Get initial height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        no_change_count = 0

        # print("STEP 3::::after execute_script('return document.body.scrollHeight')")
        # time.sleep(10)

        for i in range(max_scrolls):
            # 2. Scroll to the bottom using Physical Keys
            # Keys.END is the most reliable way to trigger "load more" events
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            except:
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )

            # 3. Wait for content to load
            # Yandex needs time to fetch images and render DOM
            time.sleep(0.5)

            # 4. Calculate new height
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            # 5. Logic: Did the page grow?
            if new_height > last_height:
                print(f"   ✓ New content loaded (Scroll {i+1})")
                last_height = new_height
                no_change_count = 0  # Reset patience
            else:
                # Height didn't change. Is it the end, or just lag?
                no_change_count += 1
                print(f"   ? No height change (Attempt {no_change_count}/3)")

                # OPTIONAL: Try to find and click the button specifically if stuck
                # (Only if you suspect the button requires a click to proceed)
                if no_change_count == 2:
                    try:
                        btn = self.driver.find_element(
                            By.CSS_SELECTOR, ".FetchListButton-Button"
                        )
                        # if btn.is_displayed():
                        #     print("   → Clicking 'Show more' button to unblock...")
                        #     self.driver.execute_script("arguments[0].click();", btn)
                        #     time.sleep(3)
                    except:
                        pass

                if no_change_count >= 3:
                    print("✓ Page height stable. Reached the end.")
                    break

        print(f"→ Scrolling complete. Final Height: {last_height}")
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

    def step5_to_10_process_thumbnail(self, thumbnail_element_ignored, index, total):
        """Steps 5-10: Re-find thumbnail -> Click -> Download -> Save -> Close"""
        # Note: We ignore the passed 'thumbnail_element_ignored' because it is likely stale.
        # We re-find the element by index.

        print("\n" + "-" * 60)
        print(f"Processing Image {index}/{total}")
        print("-" * 60)

        thumbnail = None

        # --- STALE ELEMENT PROTECTION: Re-acquire the thumbnail by index ---
        try:
            # We use the same selectors as Step 4 to find the fresh list
            selectors = [
                ".serp-item",
                ".SerpItem",
                "[class*='serp-item']",
                "a[href*='rpt=imageview']",
            ]

            found_fresh = False
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                # Ensure we have enough elements to grab the current index
                if len(elements) >= index:
                    thumbnail = elements[index - 1]  # Convert 1-based index to 0-based
                    found_fresh = True
                    # print(f"[{index}] ✓ Re-acquired fresh thumbnail element")
                    break

            if not found_fresh:
                print(
                    f"[{index}] ✗ Could not find thumbnail at index {index}. Grid might have changed."
                )
                return False

        except Exception as e:
            print(f"[{index}] ✗ Error re-acquiring thumbnail: {e}")
            return False
        # ---------------------------------------------------------------

        try:
            # Get thumbnail image URL (for initial reference)
            thumbnail_url = None
            thumbnail_data = None
            try:
                imgs = thumbnail.find_elements(By.TAG_NAME, "img")
                if imgs:
                    thumbnail_url = imgs[0].get_attribute("src")
                    if thumbnail_url and thumbnail_url.startswith("http"):
                        # print(f"[{index}] → Downloading thumbnail for comparison...")
                        thumbnail_data = self.download_image_data(thumbnail_url)
            except:
                pass

            # STEP 5: Click thumbnail to open preview (Image 4)
            print(f"[{index}] Step 5: Clicking thumbnail...")

            # Scroll to element to ensure it's rendered
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", thumbnail
            )
            time.sleep(1)  # Small pause after scroll

            try:
                thumbnail.click()
            except:
                self.driver.execute_script("arguments[0].click();", thumbnail)

            print(f"[{index}] ✓ Preview opened")
            print(f"[{index}] ⏸ Waiting 5 seconds to analyze preview...")
            time.sleep(1)

            # Get PREVIEW image
            print(f"[{index}] → Collecting preview image...")
            preview_url = None
            preview_data = None

            try:
                # UPDATED PREVIEW SELECTORS (From previous fix)
                preview_selectors = [
                    "img.MMImage-Origin",
                    ".MMImageContainer img",
                    ".MediaViewer-Image",
                    ".Modal-Content img",
                    "img[style*='max-height']",
                ]

                preview_img = None

                # Strategy 1: Specific Selectors
                for selector in preview_selectors:
                    try:
                        imgs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for img in imgs:
                            if img.is_displayed() and img.size["width"] > 100:
                                preview_img = img
                                break
                        if preview_img:
                            break
                    except:
                        continue

                # Strategy 2: Fallback to largest image
                if not preview_img:
                    all_imgs = self.driver.find_elements(By.TAG_NAME, "img")
                    largest_area = 0
                    for img in all_imgs:
                        try:
                            if img.is_displayed():
                                area = img.size["width"] * img.size["height"]
                                if area > largest_area and area > 50000:
                                    largest_area = area
                                    preview_img = img
                        except:
                            pass

                # Process preview URL
                if preview_img:
                    preview_url = preview_img.get_attribute("src")
                    if preview_url and preview_url.startswith("//"):
                        preview_url = "https:" + preview_url

                    if preview_url:
                        import html

                        preview_url = html.unescape(preview_url)
                        print(f"[{index}]   → Preview URL: {preview_url[:60]}...")

                        if preview_url.startswith("http"):
                            preview_data = self.download_image_data(preview_url)
                            if preview_data:
                                print(f"[{index}] ✓ Preview image downloaded")

            except Exception as e:
                print(f"[{index}] ⚠ Could not get preview image: {str(e)[:40]}")

            # STEP 6: Click download button
            print(f"[{index}] Step 6: Looking for download button...")
            download_button = None

            download_selectors = [
                "a[download]",
                "button[download]",
                "a[href][class*='Button']",
                ".MMButton",
                "a[target='_blank']",
            ]

            for selector in download_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        if btn.is_displayed():
                            # Heuristic checks
                            aria = (btn.get_attribute("aria-label") or "").lower()
                            cls = (btn.get_attribute("class") or "").lower()
                            if (
                                "download" in aria
                                or "download" in cls
                                or btn.get_attribute("target") == "_blank"
                            ):
                                download_button = btn
                                break
                    if download_button:
                        print(f"[{index}] ✓ Found download button: {selector}")
                        break
                except:
                    continue

            # STEP 7: Click download -> New window opens
            success = False
            if download_button:
                try:
                    print(f"[{index}] Step 7: Clicking download button...")
                    original_windows = set(self.driver.window_handles)

                    try:
                        download_button.click()
                    except:
                        self.driver.execute_script(
                            "arguments[0].click();", download_button
                        )

                    time.sleep(3)  # Wait for window
                    new_windows = set(self.driver.window_handles) - original_windows

                    if new_windows:
                        new_window = list(new_windows)[0]
                        self.driver.switch_to.window(new_window)
                        # print(f"[{index}] ✓ Switched to new window")
                        time.sleep(1)

                        # Collect images in new window
                        candidate_urls = []

                        # Check current URL
                        if any(
                            x in self.driver.current_url.lower()
                            for x in [".jpg", ".png", ".jpeg", ".webp"]
                        ):
                            candidate_urls.append(self.driver.current_url)

                        # Find img tags
                        imgs = self.driver.find_elements(By.TAG_NAME, "img")
                        for i_elem in imgs:
                            src = i_elem.get_attribute("src")
                            if (
                                src
                                and src.startswith("http")
                                and src not in candidate_urls
                            ):
                                candidate_urls.append(src)

                        # Logic to pick best image
                        # (Simplified for brevity: Pick largest file or compare hash)
                        best_match_data = None
                        best_match_url = None

                        if len(candidate_urls) > 0:
                            # Try the first/largest one
                            best_match_url = candidate_urls[0]
                            best_match_data = self.download_image_data(best_match_url)

                            if best_match_data:
                                if self.save_image(
                                    best_match_url, best_match_data, index
                                ):
                                    success = True

                        # STEP 8: Close new window
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        print(f"[{index}] ✓ Returned to main window")
                    else:
                        print(f"[{index}] ⚠ No new window opened")

                except Exception as e:
                    print(f"[{index}] ✗ Download flow error: {e}")
                    # Ensure we are back on main window
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.main_window)

            # Fallback to preview
            if not success and preview_data and preview_url:
                print(f"[{index}] → Using preview image as fallback...")
                if self.save_image(preview_url, preview_data, index):
                    success = True

            # STEP 8: Close preview panel
            # print(f"[{index}] Step 8: Closing preview panel...")
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
            except:
                pass

            return True

        except Exception as e:
            print(f"[{index}] ✗ Critical Error: {str(e)[:60]}")
            try:
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
