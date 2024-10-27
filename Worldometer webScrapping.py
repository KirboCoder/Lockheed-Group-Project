import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_worldometer_population():
    population_url = 'https://www.worldometers.info/world-population/population-by-country/'
    response = requests.get(population_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'example2'})
    
    data = []
    for row in table.find_all('tr')[1:]:  # Skip the header row
        columns = row.find_all('td')
        if len(columns) >= 12:
            data.append({
                'Country': columns[1].text.strip(),
                'Population': columns[2].text.strip(),
                'Yearly Change': columns[3].text.strip(),
                'Net Change': columns[4].text.strip(),
                'Density': columns[5].text.strip(),
                'Land Area': columns[6].text.strip(),
                'Migrants': columns[7].text.strip(),
                'Median Age': columns[9].text.strip(),
                'World Percent': columns[11].text.strip()
            })
    
    return data

def scrape_life_expectancy(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    
    life_expectancy_data = []
    for row in table.find_all('tr')[1:]:  # Skip the header row
        columns = row.find_all('td')
        if len(columns) >= 4:
            life_expectancy_data.append({
                'Country': columns[1].text.strip(),
                'Life Expectancy (Both)': columns[2].text.strip(),
                'Life Expectancy (Male)': columns[3].text.strip(),
                'Life Expectancy (Female)': columns[4].text.strip()
            })
    
    return life_expectancy_data

def scrape_gdp_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'example2'})
    
    gdp_data = []
    for row in table.find_all('tr')[1:]:  # Skip the header row
        columns = row.find_all('td')
        if len(columns) >= 7:
            gdp_data.append({
                'Country': columns[1].text.strip(),
                'GDP (nominal)': columns[2].text.strip(),
                'GDP Growth': columns[4].text.strip(),
                'GDP per capita': columns[6].text.strip()
            })
    
    return gdp_data

# Scrape population data
population_data = scrape_worldometer_population()

# Scrape life expectancy data
life_expectancy_url = 'https://www.worldometers.info/demographics/life-expectancy/'
life_expectancy_data = scrape_life_expectancy(life_expectancy_url)

# Scrape GDP data
gdp_url = 'https://www.worldometers.info/gdp/gdp-by-country/'
gdp_data = scrape_gdp_data(gdp_url)

# Combine all data
combined_data = []
for pop_item in population_data:
    country = pop_item['Country']
    combined_item = pop_item.copy()
    
    # Add life expectancy data
    life_exp_match = next((item for item in life_expectancy_data if item['Country'] == country), None)
    if life_exp_match:
        combined_item.update({
            'Life Expectancy (Both)': life_exp_match['Life Expectancy (Both)'],
            'Life Expectancy (Male)': life_exp_match['Life Expectancy (Male)'],
            'Life Expectancy (Female)': life_exp_match['Life Expectancy (Female)']
        })
    
    # Add GDP data
    gdp_match = next((item for item in gdp_data if item['Country'] == country), None)
    if gdp_match:
        combined_item.update({
            'GDP (nominal)': gdp_match['GDP (nominal)'],
            'GDP Growth': gdp_match['GDP Growth'],
            'GDP per capita': gdp_match['GDP per capita']
        })
    
    combined_data.append(combined_item)

# Convert to DataFrame
df = pd.DataFrame(combined_data)

# Save to CSV
df.to_csv('country_data_worldometer_with_gdp.csv', index=False)
