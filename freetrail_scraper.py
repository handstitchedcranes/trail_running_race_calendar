import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime

# --- Configuration ---
URL = "https://fantasy.freetrail.com/events"
# Output file - consider naming it differently to avoid overwriting manually curated files
OUTPUT_JSON_FILE = 'races_scraped.json' 

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_freetrail_events(url):
    """Scrapes race data from the Freetrail Fantasy events page using table structure."""
    scraped_races = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        response = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Request sent. Status Code: {response.status_code}")
        response.raise_for_status()
        logging.info(f"Successfully fetched content from {response.url}")

        # --- TEMPORARY DEBUG: Save HTML (Optional) ---
        try:
            with open("freetrail_debug.html", "w", encoding="utf-8") as html_file:
                html_file.write(response.text)
            logging.info("Saved fetched HTML to freetrail_debug.html for inspection.")
        except Exception as e:
            logging.error(f"Could not save debug HTML file: {e}")
        # --- END DEBUG ---

        soup = BeautifulSoup(response.text, 'html.parser')

        # --- Updated Parsing Logic for Table ---
        # Find the table body - assuming there's only one main table body for events
        # You might need to adjust this selector if there are multiple tables
        table_body = soup.find('tbody') 

        if not table_body:
            logging.warning("Could not find the main table body ('tbody'). Website structure might have changed or table is missing.")
            return []

        # Find all table rows within the body
        rows = table_body.find_all('tr')

        if not rows:
            logging.warning("Found table body, but no table rows ('tr') within it.")
            return []

        logging.info(f"Found {len(rows)} table rows.")

        for row in rows:
            # Get all table data cells in the current row
            cells = row.find_all('td')

            # Expecting at least 4 cells based on the HTML snippet (Name, Status, Date, Location)
            if len(cells) >= 4:
                try:
                    # Extract Name (from the first cell)
                    name_tag = cells[0].find('div', class_='font-semibold').find('a')
                    name = name_tag.text.strip() if name_tag else "Name Not Found"

                    # Extract Date (from the third cell)
                    date_str = cells[2].text.strip()

                    # Extract Location (from the fourth cell)
                    # Get the text of the div containing the flag span and location text
                    location_div = cells[3].find('div', class_='capitalize')
                    # Extract all text, which might include hidden/extra whitespace if structure changes
                    location = location_div.text.strip() if location_div else "Location Not Found"
                    # A potentially safer way if spans interfere, but requires checking:
                    # location = ''.join(location_div.find_all(text=True, recursive=False)).strip()

                    if name == "Name Not Found" or location == "Location Not Found" or not date_str:
                         logging.warning(f"Incomplete data found in a row. Name='{name}', Date='{date_str}', Location='{location}'. Skipping row.")
                         continue

                    scraped_races.append({
                        'name': name,
                        'scraped_start_date': date_str, # Store the exact text scraped
                        'location': location
                    })
                    logging.info(f"Scraped: {name} ({date_str}) at {location}")

                except AttributeError:
                     # This can happen if find() returns None and we try to access .text or .find() on it
                     logging.warning(f"AttributeError while parsing a row. Structure might differ. Skipping row.")
                     continue
                except Exception as e:
                     logging.error(f"Unexpected error processing a row: {e}. Skipping row.", exc_info=True)
                     continue
            else:
                logging.warning(f"Skipping a table row because it has less than 4 cells ({len(cells)} found).")


    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError):
             logging.error(f"HTTP Error during requests to {url}: {e.response.status_code} {e.response.reason}")
             # logging.error(f"Response body: {e.response.text[:500]}...") # Optional: Log response body
        else:
             logging.error(f"Error during requests to {url}: {e}")
        return None # Indicate failure
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping: {e}", exc_info=True)
        return None # Indicate failure

    return scraped_races

def format_for_calendar_json(scraped_data):
    """Formats scraped data into the structure needed for races.json, adding placeholders."""
    calendar_races = []
    if not scraped_data:
        return calendar_races

    for race in scraped_data:
        # Placeholder generation
        # Use the scraped date string to help manual entry for start_dateTime
        # You'll need to manually add the correct T HH:MM:SS-ZZ:ZZ part and timezone.
        placeholder_start_dt = f"MANUAL_TIME_NEEDED_FROM [{race['scraped_start_date']}]"

        calendar_races.append({
            "name": race['name'],
            # --- FIELDS REQUIRING MANUAL UPDATE ---
            "start_dateTime": placeholder_start_dt, # Placeholder - NEEDS MANUAL UPDATE
            "end_dateTime": "",          # Placeholder - NEEDS MANUAL UPDATE (or estimation)
            "timeZone": "",              # Placeholder - NEEDS MANUAL UPDATE (use IANA format like 'America/Denver')
            "livestream_link": "",       # Placeholder - NEEDS MANUAL UPDATE (if available)
            "description": f"Date Scraped: {race['scraped_start_date']}", # Can add distance etc. manually
            # --- FIELDS FROM SCRAPER ---
            "location": race['location']
        })
    return calendar_races

def save_to_json(data, filename):
    """Saves the data to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False) # Use indent for readability
        logging.info(f"Successfully saved {len(data)} races to {filename}")
    except IOError as e:
        logging.error(f"Error writing to file {filename}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred saving JSON: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting Freetrail Fantasy event scraper...")
    scraped_data = scrape_freetrail_events(URL)

    if scraped_data is not None: # Check if scraping succeeded
        if scraped_data:
            formatted_data = format_for_calendar_json(scraped_data)
            save_to_json(formatted_data, OUTPUT_JSON_FILE)
        else:
             logging.warning("Scraping finished, but no race data was extracted.")
    else:
         logging.error("Scraping process failed.")

    logging.info("Scraper finished.")