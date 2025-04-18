import requests
import json
import csv
import time
import re
from bs4 import BeautifulSoup
import pycountry
from datetime import datetime
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_year_range():
    current_year = datetime.now().year
    # Go back 7 years from the *previous* year, as current year data might be incomplete
    end_year = current_year - 1
    start_year = end_year - 7
    return start_year, end_year # Return end_year instead of current_year for more reliable data

def clean_numeric_value(value):
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return None

    # Handle potential edge cases like 'N/A', empty strings, etc.
    if value is None or value.strip().lower() in ['n/a', 'na', '', '-']:
        return None

    # Remove currency symbols, commas, percent signs, and extra whitespace
    value = re.sub(r'[$,%]', '', value).strip()
    # Look for the first valid number pattern (int or float, possibly negative)
    match = re.search(r'-?\d+(?:,\d{3})*(?:\.\d+)?', value.replace(',', '')) # Handle internal commas before search
    if match:
        try:
            # Remove any remaining internal commas before converting
            return float(match.group(0).replace(',', ''))
        except ValueError:
            return None # Should not happen with the regex, but safety first
    return None


def get_currency_info():
    url = "https://en.wikipedia.org/wiki/List_of_circulating_currencies"
    currency_data = {}
    try:
        logging.info("Fetching currency data from Wikipedia...")
        response = requests.get(url, timeout=15)
        response.raise_for_status() # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the correct table (might change, adjust selector if needed)
        # Let's look for a table with specific headers
        target_headers = ["State or territory", "Currency", "Symbol", "ISO code"]
        table = None
        for t in soup.find_all('table', {'class': 'wikitable'}):
            headers = [th.get_text(strip=True) for th in t.find_all('th')]
            if all(h in headers for h in target_headers):
                 # Check if the first few columns match expected content pattern
                 first_row_cols = t.find('tr').find_all('td') if t.find('tr') else []
                 # This check is heuristic, might need adjustment if wiki page changes drastically
                 if len(first_row_cols) >= 4 and first_row_cols[3].get_text(strip=True).isupper() and len(first_row_cols[3].get_text(strip=True)) == 3:
                    table = t
                    logging.info("Found currency table on Wikipedia.")
                    break # Found a likely candidate

        if not table:
            logging.warning("Could not find the expected currency table on Wikipedia.")
            return {}

        for row in table.find_all('tr')[1:]: # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 4:
                # Handle potential footnotes/references in country names
                country_cell = cols[0]
                country_name = country_cell.get_text(strip=True)
                # Attempt to clean common footnote patterns like [a], [1], etc.
                country_name = re.sub(r'\[.*?\]', '', country_name).strip()

                currency_name = cols[1].get_text(strip=True)
                currency_symbol = cols[2].get_text(strip=True) # Original script missed symbol, adding it
                iso_code = cols[3].get_text(strip=True)

                # Use lower case country name as key for easier matching
                # Handle cases where multiple countries share a currency (e.g., Eurozone)
                # The Wikipedia page lists multiple countries in the first cell sometimes
                # We need to associate the currency with *each* country mentioned
                
                # Simple split by common separators, might need refinement
                countries = re.split(r', | and ', country_name)
                
                for country in countries:
                    country = country.strip()
                    if country: # Ensure not empty string after split
                         # Basic normalization (e.g., remove "The ")
                        if country.lower().startswith("the "):
                            country = country[4:]

                        currency_data[country.lower()] = {
                            "Currency Name": currency_name,
                            "Currency Symbol": currency_symbol,
                            "ISO Code": iso_code
                        }
        logging.info(f"Processed {len(currency_data)} currency entries.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Wikipedia currency data: {e}")
    except Exception as e:
        logging.error(f"Error parsing Wikipedia currency data: {e}")

    return currency_data


def get_world_bank_data(country_code, indicators):
    base_url = "http://api.worldbank.org/v2"
    data = {}
    start_year, end_year = get_year_range()
    # Fetch data for one extra year prior to handle potential reporting lags
    fetch_start_year = start_year - 1

    logging.debug(f"Fetching World Bank data for {country_code} ({fetch_start_year}-{end_year})")

    for indicator, key in indicators.items():
        url = f"{base_url}/country/{country_code}/indicator/{indicator}?format=json&date={fetch_start_year}:{end_year}&per_page=100" # Increase per_page just in case
        try:
            response = requests.get(url, timeout=20) # Increased timeout
            # Check for non-200 status codes
            if response.status_code != 200:
                logging.warning(f"World Bank API non-200 response for {country_code}/{indicator}: Status {response.status_code}, Response: {response.text[:200]}") # Log snippet of response
                continue # Skip this indicator for this country

            result = response.json()

            # World Bank API returns a list: [metadata, data_list]
            # Check if data_list exists and is not empty or None
            if len(result) > 1 and result[1]:
                # Sort data by year to easily find the latest available within the range
                year_data_list = sorted(result[1], key=lambda x: int(x['date']), reverse=True)

                # Store all available data points within the target range
                for year_data in year_data_list:
                    year = int(year_data['date'])
                    # Only store data within the desired final range
                    if start_year <= year <= end_year:
                        value = year_data['value']
                        # Store None if value is None, let clean_numeric_value handle it later
                        data[f"{key} {year}"] = value
            else:
                # Log if no data was returned in the expected structure
                logging.debug(f"No data found or unexpected format for {country_code}/{indicator}. API Response: {result}")

        except requests.exceptions.Timeout:
             logging.warning(f"World Bank API timeout for {country_code}/{indicator}")
        except requests.exceptions.RequestException as e:
            logging.error(f"World Bank API request error for {country_code}/{indicator}: {e}")
        except json.JSONDecodeError as e:
            logging.error(f"World Bank API JSON decode error for {country_code}/{indicator}: {e} - Response: {response.text[:200]}")
        except Exception as e:
            logging.error(f"Unexpected error fetching World Bank data for {country_code}/{indicator}: {e}")
        time.sleep(0.1) # Small delay between indicator requests

    return data

# Keep defense expenditure separate as it uses a different indicator key logic
def get_defense_expenditure(country_code):
    base_url = "http://api.worldbank.org/v2"
    indicator = "MS.MIL.XPND.GD.ZS"
    data = {}
    start_year, end_year = get_year_range()
    fetch_start_year = start_year - 1 # Fetch one extra year back

    logging.debug(f"Fetching Defense Expenditure for {country_code} ({fetch_start_year}-{end_year})")
    url = f"{base_url}/country/{country_code}/indicator/{indicator}?format=json&date={fetch_start_year}:{end_year}&per_page=100"

    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            logging.warning(f"World Bank API non-200 response for {country_code}/Defense: Status {response.status_code}, Response: {response.text[:200]}")
            return data

        result = response.json()
        if len(result) > 1 and result[1]:
            year_data_list = sorted(result[1], key=lambda x: int(x['date']), reverse=True)
            for year_data in year_data_list:
                 year = int(year_data['date'])
                 if start_year <= year <= end_year:
                    value = year_data['value']
                    data[f"Defense Expenditure (% of GDP) {year}"] = value
        else:
            logging.debug(f"No defense data found or unexpected format for {country_code}. API Response: {result}")

    except requests.exceptions.Timeout:
         logging.warning(f"World Bank API timeout for {country_code}/Defense")
    except requests.exceptions.RequestException as e:
        logging.error(f"World Bank API request error for {country_code}/Defense: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"World Bank API JSON decode error for {country_code}/Defense: {e} - Response: {response.text[:200]}")
    except Exception as e:
        logging.error(f"Unexpected error fetching defense expenditure data for {country_code}: {e}")

    return data


def get_worldometer_data():
    url = "https://www.worldometers.info/world-population/population-by-country/"
    # Define current_year here or pass it as an argument
    # Calling get_year_range() gets us the range, we need the actual current year for the header check
    current_year = datetime.now().year
    data = {}
    logging.info("Fetching population data from Worldometer...")
    try:
        # Add headers to mimic a browser
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        # Find the main population table - this might need adjustment if the site changes
        # Looking for table with id='main_table_countries_today' seems reliable for now
        table = soup.find("table", {"id": "main_table_countries_today"})

        if table is None:
            logging.error("Could not find table with id='main_table_countries_today' on Worldometer population page.")
            # Fallback: try finding a table with the expected header structure (less reliable)
            for t in soup.find_all("table"):
                thead = t.find("thead")
                if thead:
                    th_texts = [th.get_text(strip=True) for th in thead.find_all("th")]
                    # Check for some key headers
                    if "Country (or dependency)" in th_texts and "Population (2023)" in th_texts and "Density (P/Km²)" in th_texts:
                         table = t
                         logging.info("Found population table using fallback header search.")
                         break
            if table is None:
                logging.error("Fallback table search also failed on Worldometer population page.")
                return {}

        tbody = table.find("tbody")
        if not tbody:
             logging.error("Found table but could not find tbody on Worldometer population page.")
             return {}

        rows = tbody.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 12: # Ensure enough columns exist
                country = cols[1].get_text(strip=True)
                # Basic normalization (e.g., handle "United States")
                if country == "United States": country = "United States of America"

                data[country.lower()] = {
                    # Use descriptive keys, avoid relying on column index implicitly
                    'Population (Worldometer)': cols[2].get_text(strip=True),
                    'Yearly Change %': cols[3].get_text(strip=True),
                    'Net Change': cols[4].get_text(strip=True),
                    'Density (P/Km²)': cols[5].get_text(strip=True),
                    'Land Area (Km²)': cols[6].get_text(strip=True),
                    'Migrants (net)': cols[7].get_text(strip=True),
                    'Fertility Rate': cols[8].get_text(strip=True),
                    'Median Age': cols[9].get_text(strip=True),
                    'Urban Pop %': cols[10].get_text(strip=True),
                    'World Share %': cols[11].get_text(strip=True)
                }
        logging.info(f"Processed {len(data)} countries from Worldometer population data.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from Worldometer population: {e}")
    except Exception as e:
        logging.error(f"Error parsing Worldometer population data: {e}")

    return data


def get_life_expectancy_data():
    url = "https://www.worldometers.info/demographics/life-expectancy/"
    data = {}
    logging.info("Fetching life expectancy data from Worldometer...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        # Find the table - assuming the first sortable table is the one we want
        table = soup.find('table', {'class': 'table-striped'}) # More specific class often used

        if table is None:
             # Fallback: Look for a table with specific headers
             target_headers = ["Country", "Life Expectancy (both sexes)", "Female Life Expectancy", "Male Life Expectancy"]
             for t in soup.find_all("table"):
                 thead = t.find("thead")
                 if thead:
                     th_texts = [th.get_text(strip=True) for th in thead.find_all("th")]
                     if all(h in th_texts for h in target_headers):
                         table = t
                         logging.info("Found life expectancy table using fallback header search.")
                         break
             if table is None:
                logging.error("Could not find the life expectancy table on Worldometer demographics page.")
                return {}

        tbody = table.find("tbody")
        if not tbody:
             logging.error("Found table but could not find tbody on Worldometer life expectancy page.")
             return {}

        rows = tbody.find_all("tr")
        for row in rows[1:]: # Skip header row if it's part of tbody in some structures
            cols = row.find_all("td")
            if len(cols) >= 5:
                country = cols[1].get_text(strip=True)
                # Basic normalization
                if country == "United States": country = "United States of America"

                data[country.lower()] = {
                    'Life Expectancy (both)': cols[2].get_text(strip=True),
                    'Life Expectancy (female)': cols[3].get_text(strip=True),
                    'Life Expectancy (male)': cols[4].get_text(strip=True)
                }
        logging.info(f"Processed {len(data)} countries from Worldometer life expectancy data.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching life expectancy data: {e}")
    except Exception as e:
        logging.error(f"Error parsing life expectancy data: {e}")

    return data

def get_factbook_data():
    base_url = "https://raw.githubusercontent.com/factbook/factbook.json/master"

    # Simplified region list - combine all codes. Duplicates are handled by processed_codes set.
    # Original structure kept for reference but unused in loop.
    _country_codes_by_region = {
        "africa": ["ag", "ao", "bc", "bn", "by", "cd", "cf", "cg", "ci", "cm", "cn", "ct", "cv", "dj", "eg", "ek", "er", "et", "ga", "gb", "gh", "gv", "iv", "ke", "li", "lt", "ly", "ma", "mi", "ml", "mo", "mp", "mr", "mz", "ng", "ni", "od", "pu", "rw", "se", "sf", "sg", "sh", "sl", "sn", "so", "su", "to", "tp", "ts", "tz", "ug", "uv", "wa", "wi", "za", "zi"],
        "australia-oceania": ["as", "at", "bp", "cr", "fj", "fm", "fp", "kr", "nc", "nf", "nh", "nr", "nz", "pp", "ps", "rm", "tb", "tn", "tv", "um", "wf", "ws"],
        "central-america-n-caribbean": ["ac", "av", "bb", "bf", "bh", "bl", "bq", "cj", "cs", "cu", "do", "dr", "es", "gj", "gt", "ha", "ho", "jm", "mh", "nu", "pm", "rn", "rq", "sc", "st", "td", "uc", "vc", "vq"],
        "central-asia": ["kg", "kz", "ti", "tx", "uz"],
        "east-n-southeast-asia": ["bm", "bn", "cb", "ch", "hk", "id", "ja", "ks", "kt", "la", "mc", "mg", "my", "pe", "rp", "sn", "th", "tt", "tw", "vm"],
        "europe": ["al", "an", "au", "ax", "be", "bg", "bo", "bu", "cy", "da", "ee", "ei", "en", "ez", "fi", "fo", "fr", "gk", "gm", "gr", "hr", "hu", "ic", "im", "it", "je", "kv", "lg", "lh", "lo", "ls", "lu", "md", "mj", "mk", "mn", "mt", "nl", "no", "pl", "po", "ri", "ro", "si", "sm", "sp", "sv", "sw", "sz", "uk", "up", "vt"],
        "middle-east": ["ae", "am", "ba", "gg", "ir", "is", "iz", "jo", "ku", "le", "mu", "qa", "sa", "sy", "tu", "ye"],
        "north-america": ["ca", "gl", "mx", "us"],
        "south-america": ["ar", "bl", "br", "ci", "co", "ec", "gy", "ns", "pa", "pe", "sr", "uy", "ve"], # Corrected 'ci' (Cote d'Ivoire) appears again, handled by set
        "south-asia": ["af", "bg", "bt", "ce", "in", "mv", "np", "pk"]
    }
    # Create a flat list of all unique country codes
    all_country_codes = set()
    for region_codes in _country_codes_by_region.values():
        all_country_codes.update(region_codes)
    # Manually map codes to potential region folders (heuristic, might need adjustment if repo structure changes)
    # This is needed because we don't know which folder a code belongs to without iterating
    # A more robust way would be to fetch the top-level directory listing if possible, but this is simpler for now.
    region_folders = list(_country_codes_by_region.keys())

    factbook_data_by_code = {} # Store by lowercased factbook country name
    logging.info("Fetching data from CIA World Factbook JSON mirror...")

    processed_codes = set()

    # Helper to safely extract text, handling missing keys/text field
    def safe_get_text(data_dict, *keys, default='N/A'):
        temp = data_dict
        for key in keys:
            if isinstance(temp, dict):
                temp = temp.get(key)
            else:
                return default # Path broken
        if isinstance(temp, dict):
             # Handle cases where text is directly under the key or nested in 'text'
             if 'text' in temp:
                 return temp.get('text', default)
             else:
                 # Fallback: Try to represent the dict content if no 'text' found
                 # This might need refinement based on actual structures encountered
                 return json.dumps(temp) if temp else default
        elif isinstance(temp, str): # Sometimes the value is directly a string
             return temp
        return default # Return default if None or not a dict/str at the end

    # Helper to find latest year data (e.g., for GDP)
    def get_latest_year_data(data_dict, base_key_pattern, default='N/A'):
        latest_year = -1
        latest_data = default
        if not isinstance(data_dict, dict):
            return default
        # Look for keys like "Real GDP (purchasing power parity) 2023"
        year_pattern = re.compile(rf"{re.escape(base_key_pattern)}\s+(\d{{4}})")
        for key, value in data_dict.items():
            match = year_pattern.match(key)
            if match:
                year = int(match.group(1))
                if year > latest_year:
                    latest_year = year
                    latest_data = safe_get_text(value, default=default) # Get text from the value dict
        return latest_data

    # Iterate through all unique country codes
    for country_code in all_country_codes:
        if country_code in processed_codes:
            continue

        data_found = False
        # Try fetching from each possible region folder until found
        for region in region_folders:
            country_url = f"{base_url}/{region}/{country_code}.json"
            logging.debug(f"Attempting to fetch Factbook data for {country_code} from region {region}")
            try:
                response = requests.get(country_url, timeout=15)
                if response.status_code == 200:
                    data_found = True
                    country_data = response.json()

                    # Extract Country Name (handle potential variations)
                    country_name_data = country_data.get('Government', {}).get('Country name', {})
                    country_name = "Unknown"
                    # Prioritize short form, then long form
                    if country_name_data:
                        short_form = safe_get_text(country_name_data, 'conventional short form', default=None)
                        long_form = safe_get_text(country_name_data, 'conventional long form', default=None)
                        if short_form and short_form != 'none' and short_form != 'N/A':
                            country_name = short_form
                        elif long_form and long_form != 'none' and long_form != 'N/A':
                            country_name = long_form

                    # Basic normalization
                    if country_name == "United States": country_name = "United States of America"
                    if country_name == "Czechia": country_name = "Czech Republic" # Align with pycountry if needed
                    if country_name == "Korea, South": country_name = "South Korea"
                    if country_name == "Korea, North": country_name = "North Korea"
                    # Add more normalizations as needed based on mismatches found

                    # --- Extract Data ---
                    people_society = country_data.get('People and Society', {})
                    economy = country_data.get('Economy', {})

                    # Existing fields
                    religions = safe_get_text(people_society, 'Religions', default='N/A')
                    age_structure = people_society.get('Age structure', {})
                    age_0_14 = safe_get_text(age_structure, '0-14 years', default='N/A')
                    age_15_64 = safe_get_text(age_structure, '15-64 years', default='N/A')
                    age_65_plus = safe_get_text(age_structure, '65 years and over', default='N/A')

                    gdp_ppp = get_latest_year_data(economy.get('Real GDP (purchasing power parity)', {}), 'Real GDP (purchasing power parity)', 'N/A')
                    gdp_growth = get_latest_year_data(economy.get('Real GDP growth rate', {}), 'Real GDP growth rate', 'N/A')
                    gdp_per_capita = get_latest_year_data(economy.get('Real GDP per capita', {}), 'Real GDP per capita', 'N/A')
                    inflation_rate = get_latest_year_data(economy.get('Inflation rate (consumer prices)', {}), 'Inflation rate (consumer prices)', 'N/A')

                    gdp_official = safe_get_text(economy, 'GDP (official exchange rate)', default='N/A')
                    gdp_composition = economy.get('GDP - composition, by sector of origin', {})
                    agriculture = safe_get_text(gdp_composition, 'agriculture', default='N/A')
                    industry = safe_get_text(gdp_composition, 'industry', default='N/A')
                    services = safe_get_text(gdp_composition, 'services', default='N/A')

                    # ** NEW Fields **
                    total_population = safe_get_text(people_society, 'Population', 'total', default='N/A') # Assuming Population -> total structure
                    # If the above path doesn't work, try direct access:
                    if total_population == 'N/A':
                         total_population = safe_get_text(people_society, 'Population', default='N/A')

                    population_growth_rate = safe_get_text(people_society, 'Population growth rate', default='N/A')
                    # Handle potential nested structure for unemployment rate if simple text fails
                    unemployment_rate = safe_get_text(economy, 'Unemployment rate', 'total', default='N/A')
                    if unemployment_rate == 'N/A': # Fallback to direct text access
                        unemployment_rate = safe_get_text(economy, 'Unemployment rate', default='N/A')


                    # Store data keyed by the *Factbook's* country name (lowercased) for later merging
                    factbook_data_by_code[country_name.lower()] = {
                        "Factbook Country Name": country_name, # Keep original case for reference if needed
                        # People & Society
                        "Population (Factbook)": total_population,
                        "Population Growth Rate (Factbook)": population_growth_rate,
                        "Religions (Factbook)": religions,
                        "Age Structure 0-14% (Factbook)": age_0_14,
                        "Age Structure 15-64% (Factbook)": age_15_64,
                        "Age Structure 65+% (Factbook)": age_65_plus,
                        # Economy
                        "Unemployment Rate (Factbook)": unemployment_rate,
                        "GDP (PPP) (Factbook)": gdp_ppp,
                        "GDP Growth Rate (Factbook)": gdp_growth,
                        "GDP Per Capita (PPP) (Factbook)": gdp_per_capita, # Clarified PPP
                        "GDP (Official Exchange Rate) (Factbook)": gdp_official,
                        "Inflation Rate (Factbook)": inflation_rate,
                        "GDP Comp. - Agriculture % (Factbook)": agriculture,
                        "GDP Comp. - Industry % (Factbook)": industry,
                        "GDP Comp. - Services % (Factbook)": services
                    }
                    logging.info(f"Processed Factbook: {country_name} ({country_code}) from region {region}")
                    processed_codes.add(country_code)
                    break # Stop trying regions once found

                elif response.status_code == 404:
                    logging.debug(f"Factbook data not found for {country_code} in region {region} (404)")
                    # Continue to the next region
                else:
                    logging.warning(f"Failed to fetch Factbook data for {country_code} in region {region}: Status {response.status_code}")
                    # Optionally break or continue depending on whether non-404 errors should stop region search
                    # break # Let's break on non-404 errors for a specific code

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching Factbook data for {country_code} in region {region}: {e}")
                # Optionally break or continue
                # break
            except json.JSONDecodeError as e:
                 logging.error(f"Error decoding Factbook JSON for {country_code} in region {region}: {e}")
                 data_found = True # Mark as found to prevent logging 'not found' later, even though processing failed
                 break # Stop trying regions if JSON is invalid
            except Exception as e:
                logging.error(f"Error processing Factbook country {country_code} in region {region}: {e}")
                data_found = True # Mark as found to prevent logging 'not found' later
                break # Stop trying regions on unexpected error
            time.sleep(0.1) # Politeness delay between requests

        if not data_found and country_code not in processed_codes:
            logging.warning(f"Factbook data could not be found for code {country_code} in any region.")
            processed_codes.add(country_code) # Add to processed set even if not found to avoid repeated attempts/warnings if structure changes

    logging.info(f"Finished fetching Factbook data. Processed {len(factbook_data_by_code)} countries successfully.")
    return factbook_data_by_code

def clean_religion_data(religions_str):
    # Handle None or non-string input
    if not isinstance(religions_str, str) or religions_str.lower() in ['n/a', 'none', '']:
        return {}

    # Improved list, handle variations (e.g., Roman Catholic)
    main_religions_map = {
        'Catholic': ['catholic'],
        'Protestant': ['protestant', 'anglican', 'lutheran', 'evangelical', 'presbyterian', 'methodist', 'baptist'], # Group common protestant denominations
        'Orthodox': ['orthodox'],
        'Other Christian': ['christian', 'mormon', 'jehovah\'s witness'], # Catch other specific Christian groups + general 'Christian' if not Catholic/Protestant/Orthodox
        'Muslim': ['muslim', 'sunni', 'shia', 'shi\'a'],
        'Jewish': ['jewish', 'judaism'],
        'Hindu': ['hindu'],
        'Buddhist': ['buddhist'],
        'Folk Religion': ['folk religion', 'animist', 'shamanist', 'traditional'], # Group indigenous/folk
        'Unaffiliated': ['unaffiliated', 'none', 'atheist', 'agnostic', 'secular'],
        'Other': ['other', 'sikh', 'baháʼí', 'baha\'i', 'zoroastrian', 'jain', 'spiritualist'] # Catch remaining specified or 'other'
    }

    # Reverse map for quick lookup: 'catholic' -> 'Catholic'
    religion_lookup = {variation: main_group for main_group, variations in main_religions_map.items() for variation in variations}

    extracted_religions = {main_group: 0.0 for main_group in main_religions_map.keys()}
    total_accounted_percentage = 0.0

    # Split by common delimiters like comma, semicolon, newline, and potentially 'note:'
    # Remove parenthetical notes first as they often contain non-percentage info
    cleaned_str = re.sub(r'\(.*?\)', '', religions_str).strip()
    # Split entries - handle cases like "Muslim 90%, Christian 10%" or "Muslim 90% (official); Christian 10%"
    entries = re.split(r'[;\n,]', cleaned_str)

    for entry in entries:
        entry = entry.strip().lower()
        if not entry or entry.startswith('note:'):
            continue

        # More robust percentage extraction - allows for space before %
        match = re.search(r'(\d{1,3}(?:\.\d+)?)\s*%', entry)
        percentage = 0.0
        religion_name_part = entry # Assume the whole entry is the name part initially

        if match:
            try:
                percentage = float(match.group(1))
                # Remove the percentage part to better identify the religion name
                religion_name_part = entry[:match.start()].strip() + entry[match.end():].strip()
                religion_name_part = religion_name_part.replace('%','').strip() # Clean up any stray % if regex was too broad
            except ValueError:
                percentage = 0.0 # Ignore if number conversion fails

        if percentage == 0.0: # Skip if no valid percentage found for this entry
             continue

        found_match = False
        # Check against specific variations first
        for variation, main_group in religion_lookup.items():
             # Use word boundaries to avoid partial matches (e.g., 'roman' in 'romanian orthodox')
             if re.search(rf'\b{re.escape(variation)}\b', religion_name_part):
                # Check if it's a subgroup already covered (e.g., don't add to 'Other Christian' if already added to 'Protestant')
                is_subgroup = False
                if main_group == 'Other Christian':
                    for specific_group in ['Catholic', 'Protestant', 'Orthodox']:
                        if extracted_religions.get(specific_group, 0) > 0 and any(re.search(rf'\b{v}\b', religion_name_part) for v in main_religions_map[specific_group]):
                            is_subgroup = True
                            break
                if not is_subgroup:
                    extracted_religions[main_group] += percentage
                    total_accounted_percentage += percentage
                    found_match = True
                    break # Stop after first match for this entry

        # If no specific match, add to 'Other' (but only if a percentage was found)
        # This logic might be too aggressive, consider refining if 'Other' becomes too large
        # if not found_match and percentage > 0:
        #     extracted_religions['Other'] += percentage
        #     total_accounted_percentage += percentage

    # Normalize percentages if they exceed 100 (simple scaling)
    # if total_accounted_percentage > 100.1: # Allow small rounding errors
    #     logging.warning(f"Religion percentages sum to {total_accounted_percentage} for input: {religions_str[:50]}... Normalizing.")
    #     scale_factor = 100.0 / total_accounted_percentage
    #     for religion in extracted_religions:
    #         extracted_religions[religion] *= scale_factor

    # Add remaining percentage to 'Unaffiliated' or 'Other' if sum is less than ~99
    # This is heuristic and might misallocate
    # if 0 < total_accounted_percentage < 99.0:
    #      remainder = 100.0 - total_accounted_percentage
    #      # Prefer adding to Unaffiliated if it exists, otherwise Other
    #      if extracted_religions.get('Unaffiliated', 0) > 0 or 'unaffiliated' in religions_str.lower() or 'none' in religions_str.lower():
    #           extracted_religions['Unaffiliated'] = extracted_religions.get('Unaffiliated', 0) + remainder
    #      else:
    #           extracted_religions['Other'] = extracted_religions.get('Other', 0) + remainder


    # Filter out religions with 0% and sort by percentage descending
    final_religions = {k: round(v, 2) for k, v in extracted_religions.items() if v > 0.01} # Use a small threshold
    sorted_religions = dict(sorted(final_religions.items(), key=lambda item: item[1], reverse=True))

    return sorted_religions


def get_all_country_data():
    # World Bank Indicators (using standard codes)
    # SP.POP.TOTL - Population, total
    # NY.GDP.MKTP.CD - GDP (current US$)
    # NY.GDP.MKTP.KD.ZG - GDP growth (annual %)
    # NY.GDP.PCAP.CD - GDP per capita (current US$)
    # SL.UEM.TOTL.ZS - Unemployment, total (% of total labor force) (modeled ILO estimate)
    # SP.POP.GROW - Population growth (annual %)
    indicators = {
        "SP.POP.TOTL": "Population WB", # Rename to avoid clash with Worldometer
        "NY.GDP.MKTP.CD": "GDP (Current US$)",
        "NY.GDP.MKTP.KD.ZG": "GDP Growth (Annual %)",
        "NY.GDP.PCAP.CD": "GDP Per Capita (Current US$)",
        "SL.UEM.TOTL.ZS": "Unemployment Rate (%)",
        "SP.POP.GROW": "Population Growth Rate (%)",
    }

    # Fetch data from all sources
    worldometer_pop_data = get_worldometer_data()
    life_expectancy_data = get_life_expectancy_data()
    factbook_data = get_factbook_data() # Keyed by lowercased factbook country name
    currency_data = get_currency_info() # Keyed by lowercased wikipedia country name

    all_data = []
    processed_countries = set()

    # Use pycountry as the primary list of countries
    logging.info(f"Processing {len(pycountry.countries)} countries from pycountry list...")
    for country in pycountry.countries:
        country_name = country.name
        alpha2_code = country.alpha_2
        alpha3_code = country.alpha_3
        numeric_code = country.numeric
        country_key_pyc = country_name.strip().lower() # Key for matching based on pycountry name

        # Handle potential pycountry name variations needed for matching
        country_key_match = country_key_pyc
        if country_key_pyc == "united states": country_key_match = "united states of america"
        if country_key_pyc == "czech republic": country_key_match = "czechia" # For Factbook matching if needed
        # Add more specific normalizations here if needed

        logging.info(f"Processing: {country_name} ({alpha3_code})")

        country_data = {
            "Country": country_name,
            "Alpha-2": alpha2_code,
            "Alpha-3": alpha3_code,
            "Numeric Code": numeric_code,
        }
        processed_countries.add(country_key_pyc) # Track processed countries

        # --- Currency Data (Match on pycountry name) ---
        currency_info = currency_data.get(country_key_match) or currency_data.get(country_key_pyc)
        if currency_info:
            country_data.update(currency_info)
        else:
            # Try matching common variations if initial match failed
            if country_key_pyc == "congo, the democratic republic of the":
                 currency_info = currency_data.get("democratic republic of the congo")
            elif country_key_pyc == "korea, republic of":
                 currency_info = currency_data.get("south korea")
            elif country_key_pyc == "korea, democratic people's republic of":
                 currency_info = currency_data.get("north korea")
            # Add more fallbacks as needed

            if currency_info:
                 country_data.update(currency_info)
            else:
                 country_data["Currency Name"] = "N/A"
                 country_data["Currency Symbol"] = "N/A"
                 country_data["ISO Code"] = "N/A"
                 logging.debug(f"No currency info found for {country_name}")


        # --- World Bank Data (using Alpha-3 code) ---
        # Use Alpha-3 code which is more reliable for World Bank API
        wb_country_code = alpha3_code # World Bank often uses ISO Alpha-3
        # Some countries might have specific codes (e.g., XKX for Kosovo)
        if country_name == "Kosovo": wb_country_code = "XKX"

        world_bank_stats = get_world_bank_data(wb_country_code, indicators)
        defense_data = get_defense_expenditure(wb_country_code)
        country_data.update(world_bank_stats)
        country_data.update(defense_data)

        # --- Worldometer Population Data (Match on pycountry name) ---
        wm_pop_info = worldometer_pop_data.get(country_key_match) or worldometer_pop_data.get(country_key_pyc)
        if wm_pop_info:
            country_data.update(wm_pop_info)
        else:
             logging.debug(f"No Worldometer population info found for {country_name}")

        # --- Worldometer Life Expectancy Data (Match on pycountry name) ---
        wm_le_info = life_expectancy_data.get(country_key_match) or life_expectancy_data.get(country_key_pyc)
        if wm_le_info:
            country_data.update(wm_le_info)
        else:
             logging.debug(f"No Worldometer life expectancy info found for {country_name}")

        # --- Factbook Data (Match on pycountry name, using normalized key) ---
        fb_info = factbook_data.get(country_key_match) or factbook_data.get(country_key_pyc)
        if fb_info:
            country_data.update(fb_info)
        else:
             logging.debug(f"No Factbook info found for {country_name}")


        # --- Data Cleaning ---
        # Clean numeric values first
        cleaned_country_data = {}
        religions_raw = "N/A" # Default
        for key, value in country_data.items():
            # Keep certain fields as strings
            if key in ["Country", "Alpha-2", "Alpha-3", "Numeric Code",
                       "Currency Name", "Currency Symbol", "ISO Code",
                       "Factbook Country Name"]: # Keep original Factbook name if needed
                cleaned_country_data[key] = value
            elif key == "Religions (Factbook)":
                religions_raw = value # Store raw religion string for parsing
                cleaned_country_data[key] = value # Keep the original string as well? Or remove? Let's keep it for now.
            else:
                # Clean all other fields assumed to be potentially numeric
                cleaned_value = clean_numeric_value(value)
                cleaned_country_data[key] = cleaned_value # Store None if cleaning fails

        # Clean religion data after other cleaning
        cleaned_country_data['Religions Parsed'] = clean_religion_data(religions_raw)

        all_data.append(cleaned_country_data)
        time.sleep(0.2) # Slightly increased delay

    logging.info(f"Finished processing {len(all_data)} countries.")
    return all_data


if __name__ == "__main__":
    logging.info("Starting country data aggregation...")
    all_country_data = get_all_country_data()

    # Filter data - ensure at least the country name is present
    # Relaxed the filter compared to the original script
    verified_data = [d for d in all_country_data if d.get("Country")]
    logging.info(f"Total countries with at least a name: {len(verified_data)}")

    # --- Save to JSON ---
    json_filename = "country_data_detailed.json"
    try:
        with open(json_filename, "w", encoding='utf-8') as f:
            # Use default=str to handle potential non-serializable types like datetime if any crept in
            json.dump(verified_data, f, indent=2, ensure_ascii=False, default=str)
        logging.info(f"Data saved to '{json_filename}'.")
    except IOError as e:
        logging.error(f"Error writing JSON file {json_filename}: {e}")
    except TypeError as e:
         logging.error(f"Error serializing data to JSON: {e}")


    # --- Prepare for CSV ---
    start_year, end_year = get_year_range()
    years = range(start_year, end_year + 1)

    # Define base CSV fields
    csv_fields = [
        "Country", "Alpha-2", "Alpha-3", "Numeric Code",
        "Currency Name", "Currency Symbol", "ISO Code",
    ]

    # Dynamically add fields for year-based World Bank data
    wb_indicators_base = ["Population WB", "GDP (Current US$)", "GDP Growth (Annual %)",
                          "GDP Per Capita (Current US$)", "Unemployment Rate (%)",
                          "Population Growth Rate (%)", "Defense Expenditure (% of GDP)"]
    for indicator in wb_indicators_base:
        csv_fields.extend([f"{indicator} {year}" for year in years])

    # Add Worldometer fields
    worldometer_fields = [
        'Population (Worldometer)', 'Yearly Change %', 'Net Change', 'Density (P/Km²)',
        'Land Area (Km²)', 'Migrants (net)', 'Fertility Rate', 'Median Age',
        'Urban Pop %', 'World Share %',
        'Life Expectancy (both)', 'Life Expectancy (female)', 'Life Expectancy (male)'
    ]
    csv_fields.extend(worldometer_fields)

    # Add Factbook fields (use the keys added in get_factbook_data)
    factbook_fields = [
        "Factbook Country Name", #"Religions (Factbook)", # Keep raw string? Maybe not for main CSV
        "Population (Factbook)", "Population Growth Rate (Factbook)", "Age Structure 0-14% (Factbook)", "Age Structure 15-64% (Factbook)", "Age Structure 65+% (Factbook)",
        "Unemployment Rate (Factbook)", "GDP (PPP) (Factbook)", "GDP Growth Rate (Factbook)", "GDP Per Capita (PPP) (Factbook)",
        "GDP (Official Exchange Rate) (Factbook)", "Inflation Rate (Factbook)",
        "GDP Comp. - Agriculture % (Factbook)", "GDP Comp. - Industry % (Factbook)", "GDP Comp. - Services % (Factbook)"
    ]
    csv_fields.extend(factbook_fields)

    # Add fields for parsed religion data (Top 5)
    max_religions_in_csv = 5
    religion_fields = []
    for i in range(max_religions_in_csv):
        religion_fields.append(f"Religion {i+1} Name")
        religion_fields.append(f"Religion {i+1} Percentage")
    csv_fields.extend(religion_fields)

    # Ensure all potential keys from data are considered for headers, prevent KeyError
    all_keys = set()
    for country in verified_data:
        all_keys.update(country.keys())

    # Filter csv_fields to only include keys that actually exist in the data collected
    # (excluding the dynamically generated religion fields for now)
    final_csv_fields = [f for f in csv_fields if f in all_keys or f.startswith("Religion ")]
    # Add any missing keys found in data but not explicitly listed (should be few)
    missing_keys = [k for k in all_keys if k not in final_csv_fields and k != 'Religions Parsed' and k != 'Religions (Factbook)']
    if missing_keys:
        logging.warning(f"Adding missing keys to CSV headers: {missing_keys}")
        final_csv_fields.extend(sorted(missing_keys))


    # --- Save to CSV ---
    csv_filename = "country_data_summary.csv"
    try:
        with open(csv_filename, "w", newline='', encoding='utf-8') as f:
            # Use extrasaction='ignore' to avoid errors if a row has extra keys not in fieldnames
            writer = csv.DictWriter(f, fieldnames=final_csv_fields, extrasaction='ignore')
            writer.writeheader()
            for country in verified_data:
                row_data = country.copy() # Work on a copy

                # Flatten the parsed religion data into the row
                parsed_religions = row_data.pop('Religions Parsed', {}) # Remove the dict from the row
                sorted_religion_items = list(parsed_religions.items())

                for i in range(max_religions_in_csv):
                    if i < len(sorted_religion_items):
                        religion_name, percentage = sorted_religion_items[i]
                        row_data[f"Religion {i+1} Name"] = religion_name
                        row_data[f"Religion {i+1} Percentage"] = percentage
                    else:
                        # Fill remaining religion slots with None or empty string
                        row_data[f"Religion {i+1} Name"] = None
                        row_data[f"Religion {i+1} Percentage"] = None

                writer.writerow(row_data)
        logging.info(f"Data saved to '{csv_filename}'.")
    except IOError as e:
        logging.error(f"Error writing CSV file {csv_filename}: {e}")
    except Exception as e:
         logging.error(f"An unexpected error occurred during CSV writing: {e}")

    logging.info("Script finished.")