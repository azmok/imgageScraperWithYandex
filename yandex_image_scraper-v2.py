#!/usr/bin/env python3
"""
Yandex Reverse Image Search Scraper - GUI Version
"""

import os
import time
import requests
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(60)
        print("✓ Chrome driver initialized (Desktop Mode)\n")

    def download_image_data(self, url):
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
        print("=" * 60)
        print("STEP 1: Upload Query Image")
        print("=" * 60)
        try:
            print("→ Loading https://yandex.com/images/")
            self.driver.get("https://yandex.com/images/")
            time.sleep(3)
            self.main_window = self.driver.current_window_handle

            print("→ Looking for camera icon...")
            camera_selectors = [
                "button[aria-label*='camera']", ".search-form__camera", 
                "[class*='camera']", "input[type='file']",
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
                            file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                            break
                except: continue

            if not file_input:
                print("✗ Camera icon not found")
                return False

            abs_path = str(Path(image_path).resolve())
            file_input.send_keys(abs_path)
            print(f"✓ Image uploaded: {image_path}")
            time.sleep(4)
            return True
        except Exception as e:
            print(f"✗ Error in Step 1: {e}")
            return False

    def step2_click_similar_images(self):
        print("\n" + "=" * 60)
        print("STEP 2: Click 'Similar Images'")
        print("=" * 60)
        try:
            time.sleep(3)
            print("→ Looking for 'Similar images' button...")
            similar_texts = ["Similar images", "similar images", "Похожие изображения", "Похожие"]
            
            similar_button = None
            for text in similar_texts:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
                    for elem in elements:
                        if elem.is_displayed():
                            similar_button = elem
                            print(f"✓ Found: '{text}'")
                            break
                    if similar_button: break
                except: continue

            if not similar_button:
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if btn.is_displayed() and "similar" in btn.text.lower():
                            similar_button = btn
                            break
                except: pass

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
        print("\n" + "=" * 60)
        print("STEP 3: Infinite Scroll (Height Check)")
        print("=" * 60)
        print(f"→ Scrolling (max {max_scrolls} steps)...")

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        no_change_count = 0

        for i in range(max_scrolls):
            try:
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            except:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            time.sleep(4) # Wait for content
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            if new_height > last_height:
                print(f"   ✓ New content loaded (Scroll {i+1})")
                last_height = new_height
                no_change_count = 0
            else:
                no_change_count += 1
                print(f"   ? No height change (Attempt {no_change_count}/3)")
                if no_change_count >= 3:
                    print("✓ Page height stable. Reached the end.")
                    break
        
        print(f"→ Scrolling complete. Final Height: {last_height}")
        return True

    def step4_get_thumbnails(self):
        print("\n" + "=" * 60)
        print("STEP 4: Collect All Thumbnails")
        print("=" * 60)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        selectors = [".serp-item", ".SerpItem", "[class*='serp-item']", "a[href*='rpt=imageview']"]
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) > 5:
                    print(f"✓ Found {len(elements)} thumbnails")
                    return elements
            except: continue
            
        links = self.driver.find_elements(By.TAG_NAME, "a")
        thumbnails = [l for l in links if l.find_elements(By.TAG_NAME, "img")]
        print(f"✓ Found {len(thumbnails)} thumbnails (fallback)")
        return thumbnails

    def step5_to_10_process_thumbnail(self, ignored, index, total):
        print("\n" + "-" * 60)
        print(f"Processing Image {index}/{total}")
        print("-" * 60)

        thumbnail = None
        # --- STALE ELEMENT PROTECTION ---
        try:
            selectors = [".serp-item", ".SerpItem", "[class*='serp-item']", "a[href*='rpt=imageview']"]
            found = False
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if len(elements) >= index:
                    thumbnail = elements[index - 1]
                    found = True
                    break
            if not found: return False
        except: return False

        try:
            # Scroll & Click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thumbnail)
            time.sleep(1)
            try: thumbnail.click()
            except: self.driver.execute_script("arguments[0].click();", thumbnail)
            
            print(f"[{index}] ✓ Preview opened")
            time.sleep(3) # Wait for preview

            # Collect Preview
            preview_url = None
            preview_data = None
            preview_selectors = [
                 "img.MMImage-Origin", ".MMImageContainer img", ".MediaViewer-Image", 
                 ".Modal-Content img", "img[style*='max-height']"
            ]
            
            preview_img = None
            for sel in preview_selectors:
                try:
                    imgs = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for img in imgs:
                        if img.is_displayed() and img.size["width"] > 100:
                            preview_img = img
                            break
                    if preview_img: break
                except: continue
            
            # Fallback Preview
            if not preview_img:
                all_imgs = self.driver.find_elements(By.TAG_NAME, "img")
                max_a = 0
                for img in all_imgs:
                    try:
                        if img.is_displayed():
                            a = img.size['width'] * img.size['height']
                            if a > max_a and a > 50000:
                                max_a = a
                                preview_img = img
                    except: pass

            if preview_img:
                preview_url = preview_img.get_attribute("src")
                if preview_url and preview_url.startswith("//"): preview_url = "https:" + preview_url
                if preview_url:
                    import html
                    preview_url = html.unescape(preview_url)
                    if preview_url.startswith("http"):
                        preview_data = self.download_image_data(preview_url)

            # Find Download Button
            dl_btn = None
            dl_sels = ["a[download]", "button[download]", "a[href][class*='Button']", ".MMButton", "a[target='_blank']"]
            for sel in dl_sels:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for btn in btns:
                        if btn.is_displayed():
                            aria = (btn.get_attribute("aria-label") or "").lower()
                            cls = (btn.get_attribute("class") or "").lower()
                            if "download" in aria or "download" in cls or btn.get_attribute("target") == "_blank":
                                dl_btn = btn
                                break
                    if dl_btn: break
                except: continue

            # Click Download -> New Window
            success = False
            if dl_btn:
                try:
                    orig_wins = set(self.driver.window_handles)
                    try: dl_btn.click()
                    except: self.driver.execute_script("arguments[0].click();", dl_btn)
                    time.sleep(3)
                    new_wins = set(self.driver.window_handles) - orig_wins
                    
                    if new_wins:
                        self.driver.switch_to.window(list(new_wins)[0])
                        time.sleep(4)
                        
                        cand_urls = []
                        if any(x in self.driver.current_url.lower() for x in ['.jpg','.png','.jpeg','.webp']):
                            cand_urls.append(self.driver.current_url)
                        
                        imgs = self.driver.find_elements(By.TAG_NAME, "img")
                        for i_elem in imgs:
                            src = i_elem.get_attribute("src")
                            if src and src.startswith("http") and src not in cand_urls:
                                cand_urls.append(src)
                        
                        if cand_urls:
                            best_url = cand_urls[0]
                            best_data = self.download_image_data(best_url)
                            if best_data and self.save_image(best_url, best_data, index):
                                success = True
                        
                        self.driver.close()
                        self.driver.switch_to.window(self.main_window)
                except:
                    if len(self.driver.window_handles) > 1: self.driver.switch_to.window(self.main_window)

            # Fallback to Preview
            if not success and preview_data and preview_url:
                print(f"[{index}] → Using preview image as fallback...")
                if self.save_image(preview_url, preview_data, index):
                    success = True

            # Close Preview
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
            except: pass
            
            return True

        except:
            try: ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            except: pass
            return False

    def save_image(self, url, image_data, index):
        try:
            if url in self.downloaded_urls:
                print(f"[{index}] ⊘ Skipped (duplicate)")
                return False
            ext = Path(urlparse(url).path).suffix or ".jpg"
            if not ext or ext == ".": ext = ".jpg"
            filename = f"yandex_{index:04d}{ext}"
            filepath = self.download_folder / filename
            with open(filepath, "wb") as f: f.write(image_data)
            self.downloaded_urls.add(url)
            self.downloaded_count += 1
            print(f"[{index}] ✓ Saved: {filename}")
            return True
        except Exception as e:
            print(f"[{index}] ✗ Save failed: {e}")
            return False

    def scrape(self, query_image_path, max_scrolls=50):
        try:
            print("\n" + "=" * 60)
            print("YANDEX IMAGE SCRAPER - STARTING")
            print("=" * 60 + "\n")
            self.setup_driver()
            if not self.step1_upload_image(query_image_path): return
            self.step2_click_similar_images()
            self.step3_scroll_until_show_more(max_scrolls)
            thumbnails = self.step4_get_thumbnails()
            if not thumbnails: return
            
            print(f"\nSTEPS 5-10: Processing {len(thumbnails)} Images")
            for i, thumbnail in enumerate(thumbnails, 1):
                self.step5_to_10_process_thumbnail(thumbnail, i, len(thumbnails))
                time.sleep(1)
                
            print("\n" + "=" * 60)
            print("SCRAPING COMPLETE!")
            print(f"✓ Saved {self.downloaded_count} images to: {self.download_folder.resolve()}")
            print("=" * 60 + "\n")
        finally:
            if self.driver:
                self.driver.quit()
                print("✓ Browser closed\n")

# ==========================================
# GUI IMPLEMENTATION
# ==========================================

class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Yandex Reverse Image Scraper")
        self.root.geometry("600x350")
        self.root.resizable(False, False)

        # Style
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", padding=6, font=("Segoe UI", 10))

        # Variables
        self.image_path = tk.StringVar()
        self.output_path = tk.StringVar(value=os.path.join(os.getcwd(), "yandex_images"))
        self.max_scrolls = tk.StringVar(value="50")
        self.headless_mode = tk.BooleanVar(value=False)

        # Layout
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Query Image Selection
        ttk.Label(main_frame, text="Query Image:").grid(row=0, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.image_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_image).grid(row=0, column=2, padx=5)

        # 2. Output Folder Selection
        ttk.Label(main_frame, text="Output Folder:").grid(row=1, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.output_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_folder).grid(row=1, column=2, padx=5)

        # 3. Max Scrolls
        ttk.Label(main_frame, text="Max Scrolls:").grid(row=2, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.max_scrolls, width=10).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # 4. Headless Mode
        ttk.Checkbutton(main_frame, text="Run Headless (Hidden Browser)", variable=self.headless_mode).grid(row=3, column=1, sticky="w", padx=5, pady=10)

        # 5. Start Button
        self.start_btn = ttk.Button(main_frame, text="START SCRAPING", command=self.start_thread)
        self.start_btn.grid(row=4, column=0, columnspan=3, pady=20, ipadx=20, ipady=5)

        # Status Label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="blue")
        self.status_label.grid(row=5, column=0, columnspan=3)

    def browse_image(self):
        filename = filedialog.askopenfilename(
            title="Select Query Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.bmp")]
        )
        if filename:
            self.image_path.set(filename)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path.set(folder)

    def start_thread(self):
        """Run scraping in a separate thread to prevent GUI freezing"""
        # Validation
        img = self.image_path.get()
        if not img or not os.path.exists(img):
            messagebox.showerror("Error", "Please select a valid image file.")
            return

        # Disable button
        self.start_btn.config(state="disabled")
        self.status_label.config(text="Running... Check console for logs.", foreground="orange")
        
        # Start Thread
        threading.Thread(target=self.run_scraper, daemon=True).start()

    def run_scraper(self):
        try:
            # Get values
            img_path = self.image_path.get()
            out_folder = self.output_path.get()
            scrolls = int(self.max_scrolls.get())
            is_headless = self.headless_mode.get()

            # Run Scraper
            scraper = YandexImageScraper(out_folder, headless=is_headless)
            scraper.scrape(img_path, scrolls)

            # On Finish
            self.root.after(0, lambda: messagebox.showinfo("Success", "Scraping Completed!"))
            self.root.after(0, lambda: self.status_label.config(text="Completed Successfully", foreground="green"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred:\n{str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="Error occurred", foreground="red"))
        
        finally:
            self.root.after(0, lambda: self.start_btn.config(state="normal"))

def main():
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()