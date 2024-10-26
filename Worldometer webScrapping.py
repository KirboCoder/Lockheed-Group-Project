import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_worldometer(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'example2'})
    
    data = []
    for row in table.find_all('tr')[1:]:  # Skip the header row
        columns = row.find_all('td')
        if len(columns) >= 12:
            country = columns[1].text.strip()
            population = columns[2].text.strip()
            yearly_change = columns[3].text.strip()
            net_change = columns[4].text.strip()
            density = columns[5].text.strip()
            land_area = columns[6].text.strip()
            migrants = columns[7].text.strip()
            median_age = columns[9].text.strip()
            world_percent = columns[11].text.strip()
            
            data.append({
                'Country': country,
                'Population': population,
                'Yearly Change': yearly_change,
                'Net Change': net_change,
                'Density': density,
                'Land Area': land_area,
                'Migrants': migrants,
                'Median Age': median_age,
                'World Percent': world_percent
            })
    
    return data

def scrape_worldometer_gdp(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'example2'})
    
    gdp_data = {}
    for row in table.find_all('tr')[1:]:  # Skip the header row
        columns = row.find_all('td')
        if len(columns) >= 3:
            country = columns[1].text.strip()
            gdp = columns[2].text.strip()
            gdp_data[country] = gdp
    
    return gdp_data

def scrape_life_expectancy(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    
    life_expectancy_data = {}
    for row in table.find_all('tr')[1:]:  # Skip the header row
        columns = row.find_all('td')
        if len(columns) >= 2:
            country = columns[0].text.strip()
            life_expectancy = columns[1].text.strip()
            life_expectancy_data[country] = life_expectancy
    
    return life_expectancy_data

# Scrape population data
population_url = 'https://www.worldometers.info/world-population/population-by-country/'
population_data = scrape_worldometer(population_url)

# Scrape GDP data
gdp_url = 'https://www.worldometers.info/gdp/gdp-by-country/'
gdp_data = scrape_worldometer_gdp(gdp_url)

# Scrape life expectancy data
life_expectancy_url = 'https://www.worldometers.info/demographics/life-expectancy/'
life_expectancy_data = scrape_life_expectancy(life_expectancy_url)

# Combine all data
for item in population_data:
    country = item['Country']
    if country in gdp_data:
        item['GDP (nominal)'] = gdp_data[country]
    else:
        item['GDP (nominal)'] = 'N/A'
    
    if country in life_expectancy_data:
        item['Life Expectancy'] = life_expectancy_data[country]
    else:
        item['Life Expectancy'] = 'N/A'

# Convert data to DataFrame
df = pd.DataFrame(population_data)

# Save to CSV
df.to_csv('country_data_worldometer_extended.csv', index=False)
print("Data scraping complete. CSV file created.")