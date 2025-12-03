#!/usr/bin/env python3
"""
Yandex Reverse Image Search Scraper (CLI Version)
Robust Desktop Mode with Infinite Scroll Support
"""

import os
import time
import requests
from pathlib import Path
from urllib.parse import urlparse

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


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

        # Standard Desktop User Agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-popup-blocking")

        # IMPORTANT: Large window size ensures Sidebar Preview layout
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(60)
        print("✓ Chrome driver initialized (Desktop Mode)\n")

    def download_image_data(self, url):
        """Download image bytes without saving"""
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
        """Step 1: Upload Query Image (Robust Version)"""
        print("=" * 60)
        print("STEP 1: Upload Query Image")
        print("=" * 60)

        try:
            print("→ Loading https://yandex.com/images/")
            self.driver.get("https://yandex.com/images/")

            # Check for Captcha immediately
            if "captcha" in self.driver.title.lower() or self.driver.find_elements(
                By.CLASS_NAME, "CheckboxCaptcha"
            ):
                print("\n!!! YANDEX BLOCKED ACCESS WITH CAPTCHA !!!")
                print("Please solve the captcha manually in the browser window.")
                input("Press ENTER here after you have solved it...")

            time.sleep(3)
            self.main_window = self.driver.current_window_handle

            # 1. Try to find the file input directly (sometimes it's hidden on page)
            try:
                file_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[type='file']"
                )
                print("✓ Found hidden file input directly")
            except:
                file_input = None

            # 2. If not found, click camera icon to reveal it
            if not file_input:
                print("→ Looking for camera icon...")
                camera_selectors = [
                    "button[aria-label*='camera']",
                    ".search-form__camera",
                    "[class*='camera']",
                    ".cbir-icon",  # New Yandex selector
                ]

                clicked = False
                for selector in camera_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                elem.click()
                                print(f"✓ Clicked camera icon ({selector})")
                                clicked = True
                                break
                        if clicked:
                            break
                    except:
                        continue

                if not clicked:
                    print("✗ Camera icon not found. Yandex might have changed layout.")
                    return False

                # WAIT for the file input to appear (up to 10 seconds)
                print("→ Waiting for upload dialog...")
                try:
                    wait = WebDriverWait(self.driver, 10)
                    file_input = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "input[type='file']")
                        )
                    )
                    print("✓ File input appeared")
                except TimeoutException:
                    print("✗ Timed out waiting for file input.")
                    # SAVE DEBUG SCREENSHOT
                    debug_file = "debug_step1_fail.png"
                    self.driver.save_screenshot(debug_file)
                    print(f"  [DEBUG] Screenshot saved to: {debug_file}")
                    print("  Check this image to see if a CAPTCHA appeared.")
                    return False

            # 3. Send the file path
            abs_path = str(Path(image_path).resolve())
            file_input.send_keys(abs_path)
            print(f"✓ Image uploaded: {image_path}")

            # Wait for upload to process (the URL changes)
            time.sleep(5)
            return True

        except Exception as e:
            print(f"✗ Error in Step 1: {e}")
            self.driver.save_screenshot("debug_step1_exception.png")
            return False

    def step2_click_similar_images(self):
        """Step 2: Click 'Similar images' button"""
        print("\n" + "=" * 60)
        print("STEP 2: Click 'Similar Images'")
        print("=" * 60)

        try:
            time.sleep(3)
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
                return True

        except Exception as e:
            print(f"✗ Error in Step 2: {e}")
            return True

    def step3_scroll_until_show_more(self, max_scrolls=50):
        """Step 3: Scroll using Page Height Logic (No Button Click)"""
        print("\n" + "=" * 60)
        print("STEP 3: Infinite Scroll (Height Check)")
        print("=" * 60)
        print(f"→ Scrolling (max {max_scrolls} steps)...")

        # 1. Get initial height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        no_change_count = 0

        for i in range(max_scrolls):
            # 2. Scroll to the bottom using Physical Keys
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            except:
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )

            # 3. Wait for content to load
            time.sleep(2)

            # 4. Calculate new height
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            # 5. Logic: Did the page grow?
            if new_height > last_height:
                print(f"   ✓ New content loaded (Scroll {i+1})")
                last_height = new_height
                no_change_count = 0  # Reset patience
            else:
                no_change_count += 1
                print(f"   ? No height change (Attempt {no_change_count}/3)")

                if no_change_count >= 3:
                    print("✓ Page height stable. Reached the end.")
                    break

        print(f"→ Scrolling complete. Final Height: {last_height}")
        return True

    def step4_get_thumbnails(self):
        """Step 4: Get all thumbnail elements"""
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

        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) > 5:
                    print(f"✓ Found {len(elements)} thumbnails")
                    return elements
            except:
                continue

        print("⚠ Using fallback selector...")
        links = self.driver.find_elements(By.TAG_NAME, "a")
        thumbnails = [l for l in links if l.find_elements(By.TAG_NAME, "img")]
        print(f"✓ Found {len(thumbnails)} thumbnails (fallback)")
        return thumbnails

    def step5_to_10_process_thumbnail(self, ignored_element, index, total):
        """Steps 5-10: Stale Element Safe Processing"""
        print("\n" + "-" * 60)
        print(f"Processing Image {index}/{total}")
        print("-" * 60)

        thumbnail = None

        # --- STALE ELEMENT PROTECTION: Re-acquire by index ---
        try:
            selectors = [
                ".serp-item",
                ".SerpItem",
                "[class*='serp-item']",
                "a[href*='rpt=imageview']",
            ]
            found_fresh = False
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) >= index:
                    thumbnail = elements[index - 1]
                    found_fresh = True
                    break

            if not found_fresh:
                print(f"[{index}] ✗ Could not find thumbnail at index {index}")
                return False

        except Exception as e:
            print(f"[{index}] ✗ Error re-acquiring thumbnail: {e}")
            return False

        try:
            # STEP 5: Click thumbnail
            print(f"[{index}] Step 5: Clicking thumbnail...")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", thumbnail
            )
            time.sleep(0.5)

            try:
                thumbnail.click()
            except:
                self.driver.execute_script("arguments[0].click();", thumbnail)

            print(f"[{index}] ✓ Preview opened")
            print(f"[{index}] ⏸ Waiting 3 seconds for preview...")
            time.sleep(3)

            # GET PREVIEW IMAGE
            print(f"[{index}] → Collecting preview image...")
            preview_url = None
            preview_data = None

            # Robust Preview Selectors
            preview_selectors = [
                "img.MMImage-Origin",
                ".MMImageContainer img",
                ".MediaViewer-Image",
                ".Modal-Content img",
                "img[style*='max-height']",
            ]

            preview_img = None

            # 1. Try specific selectors
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

            # 2. Fallback: Largest Image in view
            if not preview_img:
                all_imgs = self.driver.find_elements(By.TAG_NAME, "img")
                max_area = 0
                for img in all_imgs:
                    try:
                        if img.is_displayed():
                            area = img.size["width"] * img.size["height"]
                            if area > max_area and area > 50000:
                                max_area = area
                                preview_img = img
                    except:
                        pass

            if preview_img:
                preview_url = preview_img.get_attribute("src")
                if preview_url:
                    if preview_url.startswith("//"):
                        preview_url = "https:" + preview_url
                    import html

                    preview_url = html.unescape(preview_url)

                    if preview_url.startswith("http"):
                        preview_data = self.download_image_data(preview_url)
                        if preview_data:
                            print(f"[{index}] ✓ Preview image downloaded")

            # STEP 6: Find Download Button
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
                        break
                except:
                    continue

            # STEP 7: Click Download -> New Window
            success = False
            if download_button:
                try:
                    print(f"[{index}] Step 7: Clicking download button...")
                    orig_windows = set(self.driver.window_handles)

                    try:
                        download_button.click()
                    except:
                        self.driver.execute_script(
                            "arguments[0].click();", download_button
                        )

                    time.sleep(3)
                    new_windows = set(self.driver.window_handles) - orig_windows

                    if new_windows:
                        self.driver.switch_to.window(list(new_windows)[0])
                        time.sleep(3)

                        # Collect candidates
                        cand_urls = []
                        if any(
                            x in self.driver.current_url.lower()
                            for x in [".jpg", ".png", ".jpeg", ".webp"]
                        ):
                            cand_urls.append(self.driver.current_url)

                        imgs = self.driver.find_elements(By.TAG_NAME, "img")
                        for i_elem in imgs:
                            src = i_elem.get_attribute("src")
                            if src and src.startswith("http") and src not in cand_urls:
                                cand_urls.append(src)

                        if cand_urls:
                            best_url = cand_urls[0]
                            best_data = self.download_image_data(best_url)
                            if best_data and self.save_image(
                                best_url, best_data, index
                            ):
                                success = True

                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                        print(f"[{index}] ✓ Returned to main window")
                    else:
                        print(f"[{index}] ⚠ No new window opened")

                except Exception as e:
                    print(f"[{index}] ✗ Download error: {e}")
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.main_window)

            # FALLBACK
            if not success and preview_data and preview_url:
                print(f"[{index}] → Using preview image as fallback...")
                if self.save_image(preview_url, preview_data, index):
                    success = True

            # STEP 8: Close Preview
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
            if url in self.downloaded_urls:
                print(f"[{index}] ⊘ Skipped (duplicate)")
                return False

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
        """Main scraping workflow"""
        try:
            print("\n" + "=" * 60)
            print("YANDEX IMAGE SCRAPER - STARTING")
            print("=" * 60 + "\n")

            self.setup_driver()

            if not self.step1_upload_image(query_image_path):
                print("\n✗ Failed at Step 1")
                return

            self.step2_click_similar_images()
            self.step3_scroll_until_show_more(max_scrolls)

            thumbnails = self.step4_get_thumbnails()
            if not thumbnails:
                print("\n✗ No thumbnails found")
                return

            print("\n" + "=" * 60)
            print(f"STEPS 5-10: Processing {len(thumbnails)} Images")
            print("=" * 60)

            for i, thumbnail in enumerate(thumbnails, 1):
                self.step5_to_10_process_thumbnail(thumbnail, i, len(thumbnails))
                time.sleep(1)

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
    print("Yandex Reverse Image Search Scraper (CLI)")
    print("=" * 60)

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

    scraper = YandexImageScraper(output_folder, headless=headless)
    scraper.scrape(query_image, max_scrolls)


if __name__ == "__main__":
    main()
