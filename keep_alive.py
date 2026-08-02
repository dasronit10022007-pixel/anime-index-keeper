import os
import sys
import time
import argparse
from supabase import create_client, Client
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- Parse Arguments ---
parser = argparse.ArgumentParser(description="Anime Index Keep-Alive Bot")
parser.add_argument("--offset", type=int, default=0, help="Start row index")
parser.add_argument("--limit", type=int, default=500, help="Number of rows to fetch")
args = parser.parse_args()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TEST_URL = os.environ.get("TEST_URL")
BASE_URL = "https://animeindex.embed4me.com/#"

def fetch_video_urls(offset: int, limit: int):
    # If testing a single URL, skip the database entirely!
    if TEST_URL and TEST_URL.strip():
        print(f"TEST MODE: Overriding database and testing single URL: {TEST_URL}")
        return [TEST_URL.strip()]

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_KEY missing.")
        sys.exit(1)

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"Fetching rows from index {offset} to {offset + limit}...")
    response = supabase.table("episodes_v2") \
        .select("video_id_eng, video_id_jap, video_id_hin, video_id_multi") \
        .range(offset, offset + limit - 1) \
        .execute()
    
    urls = []
    columns = ["video_id_eng", "video_id_jap", "video_id_hin", "video_id_multi"]
    
    for row in response.data:
        for col in columns:
            val = row.get(col)
            if val and str(val).strip().lower() not in ["null", "empty", ""]:
                urls.append(f"{BASE_URL}{str(val).strip()}")
                
    print(f"Total valid video URLs found in this batch: {len(urls)}")
    return urls

def play_videos(urls):
    if not urls:
        print("No valid video URLs found in this chunk.")
        return

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--mute-audio")
    
    # Fake being a real Windows computer to bypass bot detection
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    driver.set_page_load_timeout(30)
    
    try:
        for index, url in enumerate(urls):
            print(f"[{index + 1}/{len(urls)}] Simulating play for: {url}")
            try:
                driver.get(url)
                
                # Wait for the player UI to load
                time.sleep(5)
                
                # Physically click the screen to start the video and bypass autoplay blockers
                body = driver.find_element(By.TAG_NAME, "body")
                body.click()
                print("Clicked play button...")
                
                # Wait 30 seconds to guarantee a solid 20s view is recorded
                time.sleep(30)
                
            except Exception as e:
                print(f"Failed to load or click {url}: {e}")
    finally:
        driver.quit()
        print("Batch processing complete!")

if __name__ == "__main__":
    urls_to_play = fetch_video_urls(args.offset, args.limit)
    play_videos(urls_to_play)
