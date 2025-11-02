from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import traceback

url = "https://www.imdb.com/chart/top/"

options = webdriver.ChromeOptions()
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/118.0.5993.90 Safari/537.36")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)

print("🌐 Loading IMDb Top 250 page...")
time.sleep(4)

def save_page_source(note="snapshot"):
    fname = f"imdb_page_{note}.html"
    try:
        with open(fname, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Saved page source to {fname} (open in VS Code to inspect).")
    except Exception as e:
        print("Failed to save page source:", e)

try:
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table.chart.full-width tbody.lister-list tr"))
        )
        rows = driver.find_elements(By.CSS_SELECTOR, "table.chart.full-width tbody.lister-list tr")
        print(f"Selector A (table rows) found {len(rows)} elements.")
    except Exception as e_a:
        print("Selector A did not find rows or timed out. Trying fallback selectors...")
        rows = []
    if not rows:
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'li.ipc-metadata-list-summary-item'))
            )
            rows = driver.find_elements(By.CSS_SELECTOR, 'li.ipc-metadata-list-summary-item')
            print(f"Selector B (ipc list items) found {len(rows)} elements.")
        except Exception as e_b:
            print("Selector B also failed or timed out.")
            rows = []
    if not rows:
        print("⚠️ No candidate elements found. Saving page source for inspection.")
        save_page_source("no_elements")
        raise RuntimeError("No matching movie elements found on page. Inspect saved HTML.")
    try:
        print("Preview of first element text (first 800 chars):")
        print(rows[0].text[:800])
    except Exception as e:
        print("Couldn't print preview of first row:", e)

    data = []
    
    for i, el in enumerate(rows, start=1):
        rank = str(i)
        title = "N/A"
        year = "N/A"
        rating = "N/A"
        try:
            title_anchor = el.find_element(By.CSS_SELECTOR, "td.titleColumn a")
            title = title_anchor.text.strip()
            year_text = el.find_element(By.CSS_SELECTOR, "td.titleColumn span.secondaryInfo").text.strip()
            year = year_text.strip("()")
            rating = el.find_element(By.CSS_SELECTOR, "td.imdbRating strong").text.strip()
        except Exception:
            try:
                title_elem = el.find_element(By.CSS_SELECTOR, 'h3.ipc-title__text')
                title_full = title_elem.text.strip()
                if '.' in title_full:
                    _, t = title_full.split('.', 1)
                    title = t.strip()
                else:
                    title = title_full
            except Exception:
                pass

            try:
                year = el.find_element(By.CSS_SELECTOR, 'span.cli-title-metadata-item:nth-of-type(1)').text
            except Exception:
                import re
                m = re.search(r"\b(19|20)\d{2}\b", el.text)
                if m:
                    year = m.group(0)
            try:
                rating = el.find_element(By.CSS_SELECTOR, 'span.ipc-rating-star--rating').text
            except Exception:
                pass

        data.append({"Rank": rank, "Title": title, "Year": year, "Rating": rating})

    df = pd.DataFrame(data)
    df.to_csv("imdb_top_250.csv", index=False, encoding="utf-8")
    print(f"🎬 Scraping complete! Saved {len(df)} movies to imdb_top_250.csv")

except Exception as e:
    print("⚠️ Could not load movie data properly.")
    print("Error:", str(e))
    traceback.print_exc()
    save_page_source("error")
finally:
    try:
        if "--headless=new" not in " ".join(options.arguments or []):
            time.sleep(4)
    except Exception:
        pass
    driver.quit()