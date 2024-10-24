import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_cia_world_factbook(country):
    #basic cia url that takes whatever country input we want
    url = f"https://www.cia.gov/the-world-factbook/countries/{country}/"
    #This actually sends the get request to the server
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the population section and extract total population (placeholder - adjust based on actual structure))
    try:
        #This finds the GDP header, then extracts 'p' or paragraph. also checks to find the text 'total'
        population_section = soup.find('h3', text='Population')
        total_population = population_section.find_next('p').find('strong', text='total:').next_sibling.strip()
    except AttributeError:
        total_population = "Data not found"

    # Find GDP section (placeholder - adjust based on actual structure)
    try:
        #This finds the GDP header, then extracts 'p' or paragraph
        gdp_section = soup.find('h3', text='Real GDP (purchasing power parity)')
        gdp_value = gdp_section.find_next('p').get_text(strip=True)
    except AttributeError:
        gdp_value = "Data not found"

#Returns a dictionary containing the scraped data with formatted keys
    return {
        'Country': country.capitalize(),
        'Total Population': total_population,
        'GDP (PPP)': gdp_value
    }

# List of countries to scrape, can be adjusted as needed for better functionality
countries = ['saudi-arabia', 'hungary','china', 'united-kingdom', 'japan']


# Scrape data for each country
data = []
for country in countries:
    country_data = scrape_cia_world_factbook(country)
    data.append(country_data)


#Converts the collected data into a pandas DataFrame and Saves the data to a CSV file
df = pd.DataFrame(data)

df.to_csv('country_data.csv', index=False)
print("Data scraping complete. CSV file created.")