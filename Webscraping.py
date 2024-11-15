import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pycountry
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize the Selenium WebDriver
def initialize_driver():
    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--disable-gpu")  
    chrome_options.add_argument("--no-sandbox")  # Disable the sandbox for more stable execution
    return webdriver.Chrome(options=chrome_options)

# Scrape total population for a given country
def get_total_population(driver, country):
    url = f"https://www.worldometers.info/world-population/{country}-population/"
    driver.get(url)
    time.sleep(2)  # Wait for page to load
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    population_div = soup.find('div', attrs={'class': 'maincounter-number'})
    # Return population as integer, removing commas
    return int(population_div.text.strip().replace(',', '')) if population_div else None

# Scrape population data for cities in a given country
def get_population_by_cities(driver, country):
    url = f"https://www.worldometers.info/world-population/{country}-population/"
    driver.get(url)
    time.sleep(2)  # Wait for page to load
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.find('table', attrs={'class': 'table table-striped table-bordered'})
    cities, populations = [], []
    if table:
        rows = table.find_all('tr')[1:]  # Skip header row
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 3:
                cities.append(cols[1].text.strip())
                populations.append(int(cols[2].text.strip().replace(',', '')))
    return pd.DataFrame({'City': cities, 'Population': populations})

# Scrape life expectancy data from Worldometers
def scrape_life_expectancy(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    life_expectancy_data = []
    for row in table.find_all('tr')[1:]:  # Skip header row
        columns = row.find_all('td')
        if len(columns) >= 4:
            life_expectancy_data.append({
                'Country': columns[1].text.strip(),
                'Life Expectancy (Both)': float(columns[2].text.strip()),
                'Life Expectancy (Male)': float(columns[3].text.strip()),
                'Life Expectancy (Female)': float(columns[4].text.strip())
            })
    return life_expectancy_data

# Scrape GDP data from Worldometers
def scrape_gdp_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'example2'})
    gdp_data = []
    for row in table.find_all('tr')[1:]:  # Skip header row
        columns = row.find_all('td')
        if len(columns) >= 7:
            gdp_data.append({
                'Country': columns[1].text.strip(),
                'GDP (nominal)': float(columns[2].text.strip().replace('$', '').replace(',', '')),
                'GDP Growth': float(columns[4].text.strip().replace('%', '')),
                'GDP per capita': float(columns[6].text.strip().replace('$', '').replace(',', '')),
                'Year': int(columns[0].text.strip())
            })
    return gdp_data

# Scrape additional population data from Worldometers
def get_additional_population_data(session):
    population_url = 'https://www.worldometers.info/world-population/population-by-country/'
    response = session.get(population_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'example2'})
    population_data = []
    for row in table.find_all('tr')[1:]:  # Skip header row
        columns = row.find_all('td')
        if len(columns) >= 12:
            population_data.append({
                'Country': columns[1].text.strip(),
                'Population': int(columns[2].text.strip().replace(',', '')),
                'Yearly Change': float(columns[3].text.strip().replace('%', '')),
                'Net Change': int(columns[4].text.strip().replace(',', '')),
                'Density (P/Km²)': float(columns[5].text.strip()),
                'Land Area (Km²)': int(columns[6].text.strip().replace(',', '')),
                'Migrants (net)': int(columns[7].text.strip().replace(',', '')),
                'Median Age': float(columns[9].text.strip()),
                'World Share': float(columns[11].text.strip().replace('%', '')),
                'Year': int(columns[0].text.strip())
            })
    return population_data

# Get life expectancy data
def get_life_expectancy_data():
    life_expectancy_url = 'https://www.worldometers.info/demographics/life-expectancy/'
    return scrape_life_expectancy(life_expectancy_url)

# Get GDP information
def get_gdp_information():
    gdp_url = 'https://www.worldometers.info/gdp/gdp-by-country/'
    return scrape_gdp_data(gdp_url)

# Check if a country meets NATO defense spending target
def check_nato_defense_target(defense_pct_gdp):
    try:
        defense_value = float(defense_pct_gdp)
        return "Yes" if defense_value >= 2.0 else "No"
    except:
        return "Data not available"

# Get list of countries using pycountry library
def get_country_list():
    return [{'name': country.name.lower().replace(' ', '-'), 'code': country.alpha_2} 
            for country in pycountry.countries]

# Fetch GDP Growth data from World Bank API
def get_gdp_growth(session, country_code):
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=100"
    response = session.get(url)
    if response.status_code == 200:
        data_json = response.json()
        if data_json and len(data_json) > 1:
            for entry in data_json[1]:
                if entry['value'] is not None:
                    return {'value': float(entry['value']), 'year': int(entry['date'])}
    return {'value': None, 'year': None}

# Fetch Defense Expenditure data from World Bank API
def get_defense_expenditure(session, country_code):
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/MS.MIL.XPND.GD.ZS?format=json&per_page=100"
    response = session.get(url)
    if response.status_code == 200:
        data_json = response.json()
        if data_json and len(data_json) > 1:
            for entry in data_json[1]:
                if entry['value'] is not None:
                    return {'value': float(entry['value']), 'year': int(entry['date'])}
    return {'value': None, 'year': None}

# Process data for a single country
def process_country(session, country_info):
    country = country_info['name']
    country_code = country_info['code']
    driver = initialize_driver()
    data = {'Country': country.replace('-', ' ').title()}
    try:
        # Get total population
        data['Total Population'] = get_total_population(driver, country)
        
        # Get population by cities
        population_cities_df = get_population_by_cities(driver, country)
        data['Top Cities'] = population_cities_df.to_dict(orient='records')
        
        # Get GDP composition by sector
        url_economy = f"https://www.cia.gov/the-world-factbook/countries/{country}/#economy"
        driver.get(url_economy)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        sector_data = soup.find(string="GDP - composition by sector")
        if sector_data:
            parent_div = sector_data.find_parent().find_next_sibling('div')
            if parent_div:
                parts = parent_div.text.strip().split(',')
                for part in parts:
                    key_value_pair = part.split(':')
                    if len(key_value_pair) == 2:
                        key, value = key_value_pair[0].strip(), key_value_pair[1].strip()
                        data[f"GDP Composition - {key}"] = float(value.replace('%', ''))
        
        # Get GDP growth and defense expenditure from World Bank API
        gdp_growth = get_gdp_growth(session, country_code)
        defense_expenditure = get_defense_expenditure(session, country_code)
        data.update({
            'GDP Growth': gdp_growth['value'],
            'GDP Growth Year': gdp_growth['year'],
            'Defense Expenditure': defense_expenditure['value'],
            'Defense Expenditure Year': defense_expenditure['year']
        })
        
    except Exception as e:
        print(f"Error processing {data['Country']}: {e}")
    finally:
        driver.quit()
    return data

# Main function to orchestrate the scraping process
def main():
    session = requests.Session()
    country_list = get_country_list()
    all_data = []

    # Use ThreadPoolExecutor for concurrent processing of countries
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_country = {executor.submit(process_country, session, country): country for country in country_list}
        for future in as_completed(future_to_country):
            country = future_to_country[future]
            try:
                data = future.result()
                all_data.append(data)
                print(f"Processed {data['Country']}")
            except Exception as exc:
                print(f"{country['name'].title()} generated an exception: {exc}")

    # Get additional data
    population_data = get_additional_population_data(session)
    life_expectancy_data = get_life_expectancy_data()
    gdp_data = get_gdp_information()

    # Combine all data
    combined_data = []
    for pop_item in population_data:
        country_name = pop_item['Country']
        combined_item = pop_item.copy()

        # Add life expectancy data
        life_exp_match = next((item for item in life_expectancy_data if item['Country'] == country_name), None)
        if life_exp_match:
            combined_item.update({
                'Life Expectancy (Both)': life_exp_match['Life Expectancy (Both)'],
                'Life Expectancy (Male)': life_exp_match['Life Expectancy (Male)'],
                'Life Expectancy (Female)': life_exp_match['Life Expectancy (Female)']
            })

        # Add GDP data
        gdp_match = next((item for item in gdp_data if item['Country'] == country_name), None)
        if gdp_match:
            combined_item.update({
                'GDP (nominal)': gdp_match['GDP (nominal)'],
                'GDP Growth': gdp_match['GDP Growth'],
                'GDP per capita': gdp_match['GDP per capita'],
                'GDP Year': gdp_match['Year']
            })

        combined_data.append(combined_item)

    # Create DataFrames and merge data
    combined_df = pd.DataFrame(combined_data)
    main_df = pd.DataFrame(all_data)
    final_df = pd.merge(main_df, combined_df, on='Country', how='outer')

    # Save to CSV
    final_df.to_csv('combined_country_data.csv', index=False)
    print("Data has been successfully scraped and saved to 'combined_country_data.csv'.")

if __name__ == "__main__":
    main()