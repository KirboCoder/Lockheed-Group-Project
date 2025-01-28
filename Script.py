import requests
import json
import csv
import time
import re
from bs4 import BeautifulSoup
import pycountry
from datetime import datetime

def get_year_range():
    current_year = datetime.now().year
    start_year = current_year - 7
    return start_year, current_year

def clean_numeric_value(value):
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return None

    value = value.replace(',', '').strip('%')
    match = re.search(r'-?\d+\.?\d*', value)
    if match:
        return float(match.group())
    return None

def get_currency_info():
    url = "https://en.wikipedia.org/wiki/List_of_circulating_currencies"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    currency_data = {}
    table = soup.find('table', {'class': 'wikitable'})

    for row in table.find_all('tr')[1:]:
        cols = row.find_all('td')
        if len(cols) >= 4:
            country = cols[0].text.strip()
            currency_name = cols[1].text.strip()
            currency_code = cols[2].text.strip()
            iso_code = cols[3].text.strip()

            currency_data[country.lower()] = {
                "Currency Name": currency_name,
                "Currency Code": currency_code,
                "ISO Code": iso_code
            }

    return currency_data

def get_world_bank_data(country_code, indicators):
    base_url = "http://api.worldbank.org/v2"
    data = {}
    start_year, current_year = get_year_range()
    try:
        for indicator, key in indicators.items():
            response = requests.get(f"{base_url}/country/{country_code}/indicator/{indicator}?format=json&date={start_year}:{current_year}")
            if response.status_code == 200:
                result = response.json()
                if len(result) > 1 and result[1]:
                    for year_data in result[1]:
                        year = year_data['date']
                        value = year_data['value']
                        data[f"{key} {year}"] = value

  
        country_response = requests.get(f"{base_url}/country/{country_code}?format=json")
        if country_response.status_code == 200:
            country_result = country_response.json()
            if len(country_result) > 1 and country_result[1]:
                country_info = country_result[1][0]
                country_name = country_info.get('name', '')
    except Exception as e:
        print(f"World Bank API error: {e}")
    return data

def get_defense_expenditure(country_code):
    base_url = "http://api.worldbank.org/v2"
    indicator = "MS.MIL.XPND.GD.ZS"  
    start_year, current_year = get_year_range()
    data = {}
    try:
        response = requests.get(f"{base_url}/country/{country_code}/indicator/{indicator}?format=json&date={start_year}:{current_year}")
        if response.status_code == 200:
            result = response.json()
            if len(result) > 1 and result[1]:
                for year_data in result[1]:
                    year = year_data['date']
                    value = year_data['value']
                    data[f"Defense Expenditure (% of GDP) {year}"] = value
    except Exception as e:
        print(f"Error fetching defense expenditure data: {e}")
    return data

def get_worldometer_data():
    url = "https://www.worldometers.info/world-population/population-by-country/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'id': 'example2'})
            data = {}
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                country = cols[1].text.strip()
                data[country.lower()] = {
                    'Population': cols[2].text.strip(),
                    'Yearly Change': cols[3].text.strip(),
                    'Net Change': cols[4].text.strip(),
                    'Density (P/Km²)': cols[5].text.strip(),
                    'Land Area (Km²)': cols[6].text.strip(),
                    'Migrants (net)': cols[7].text.strip(),
                    'Fertility Rate': cols[8].text.strip(),
                    'Median Age': cols[9].text.strip(),
                    'Urban Pop %': cols[10].text.strip(),
                    'World Share': cols[11].text.strip()
                }
            return data
        else:
            print(f"Worldometer error: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data from Worldometer: {e}")
    return {}

def get_life_expectancy_data():
    url = "https://www.worldometers.info/demographics/life-expectancy/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'id': 'example2'})
            data = {}
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                country = cols[1].text.strip()
                data[country.lower()] = {
                    'Life Expectancy (both)': cols[2].text.strip(),
                    'Life Expectancy (female)': cols[3].text.strip(),
                    'Life Expectancy (male)': cols[4].text.strip()
                }
            return data
        else:
            print(f"Life expectancy data error: {response.status_code}")
    except Exception as e:
        print(f"Error fetching life expectancy data: {e}")
    return {}

def get_factbook_data():
    base_url = "https://raw.githubusercontent.com/factbook/factbook.json/master"
    regions = ["africa", "australia-oceania", "central-america-n-caribbean", "central-asia", "east-n-southeast-asia", "europe", "middle-east", "north-america", "south-america", "south-asia"]
    country_codes = {
        "africa": ["ag", "ao", "bc", "bn", "by", "cd", "cf", "cg", "ci", "cm", "cn", "ct", "cv", "dj", "eg", "ek", "er", "et", "ga", "gb", "gh", "gv", "iv", "ke", "li", "lt", "ly", "ma", "mi", "ml", "mo", "mp", "mr", "mz", "ng", "ni", "od", "pu", "rw", "se", "sf", "sg", "sh", "sl", "sn", "so", "su", "to", "tp", "ts", "tz", "ug", "uv", "wa", "wi", "za", "zi"],
        "australia-oceania": ["as", "at", "bp", "cr", "fj", "fm", "fp", "kr", "nc", "nf", "nh", "nr", "nz", "pp", "ps", "rm", "tb", "tn", "tv", "um", "wf", "ws"],
        "central-america-n-caribbean": ["ac", "av", "bb", "bf", "bh", "bl", "bq", "cj", "cs", "cu", "do", "dr", "es", "gj", "gt", "ha", "ho", "jm", "mh", "nu", "pm", "rn", "rq", "sc", "st", "td", "uc", "vc", "vq"],
        "central-asia": ["kg", "kz", "ti", "tx", "uz"],
        "east-n-southeast-asia": ["bm", "bn", "cb", "ch", "hk", "id", "ja", "ks", "kt", "la", "mc", "mg", "my", "pe", "rp", "sn", "th", "tt", "tw", "vm"],
        "europe": ["al", "an", "au", "ax", "be", "bg", "bo", "bu", "cy", "da", "ee", "ei", "en", "ez", "fi", "fo", "fr", "gk", "gm", "gr", "hr", "hu", "ic", "im", "it", "je", "kv", "lg", "lh", "lo", "ls", "lu", "md", "mj", "mk", "mn", "mt", "nl", "no", "pl", "po", "ri", "ro", "si", "sm", "sp", "sv", "sw", "sz", "uk", "up", "vt"],
        "middle-east": ["ae", "am", "ba", "gg", "ir", "is", "iz", "jo", "ku", "le", "mu", "qa", "sa", "sy", "tu", "ye"],
        "north-america": ["ca", "gl", "mx", "us"],
        "south-america": ["ar", "bl", "br", "ci", "co", "ec", "gy", "ns", "pa", "pe", "sr", "uy", "ve"],
        "south-asia": ["af", "bg", "bt", "ce", "in", "mv", "np", "pk"]
    }
    data = {}
    for region in regions:
        for country_code in country_codes[region]:
            country_url = f"{base_url}/{region}/{country_code}.json"
            try:
                response = requests.get(country_url)
                if response.status_code == 200:
                    country_data = response.json()
                    country_name = country_data.get('Government', {}).get('Country name', {}).get('conventional short form', {}).get('text', 'Unknown')
                    religions = country_data.get('People and Society', {}).get('Religions', {}).get('text', 'N/A')
                    age_structure = country_data.get('People and Society', {}).get('Age structure', {})
                    age_0_14 = age_structure.get('0-14 years', {}).get('text', 'N/A')
                    age_15_64 = age_structure.get('15-64 years', {}).get('text', 'N/A')
                    age_65_plus = age_structure.get('65 years and over', {}).get('text', 'N/A')
                    economy = country_data.get('Economy', {})
                    gdp_ppp = economy.get('Real GDP (purchasing power parity)', {}).get('Real GDP (purchasing power parity) 2023', {}).get('text', 'N/A')
                    gdp_growth = economy.get('Real GDP growth rate', {}).get('Real GDP growth rate 2023', {}).get('text', 'N/A')
                    gdp_per_capita = economy.get('Real GDP per capita', {}).get('Real GDP per capita 2023', {}).get('text', 'N/A')
                    gdp_official = economy.get('GDP (official exchange rate)', {}).get('text', 'N/A')
                    inflation_rate = economy.get('Inflation rate (consumer prices)', {}).get('Inflation rate (consumer prices) 2023', {}).get('text', 'N/A')
                    gdp_composition = economy.get('GDP - composition, by sector of origin', {})
                    agriculture = gdp_composition.get('agriculture', {}).get('text', 'N/A')
                    industry = gdp_composition.get('industry', {}).get('text', 'N/A')
                    services = gdp_composition.get('services', {}).get('text', 'N/A')
                    data[country_name.lower()] = {
                        "Country": country_name,
                        "Religions": religions,
                        "Age Structure (0-14)": age_0_14,
                        "Age Structure (15-64)": age_15_64,
                        "Age Structure (65+)": age_65_plus,
                        "GDP (PPP)": gdp_ppp,
                        "GDP Growth Rate": gdp_growth,
                        "GDP Per Capita": gdp_per_capita,
                        "GDP (Official Exchange Rate)": gdp_official,
                        "Inflation Rate": inflation_rate,
                        "GDP Composition - Agriculture": agriculture,
                        "GDP Composition - Industry": industry,
                        "GDP Composition - Services": services
                    }
                    print(f"Processed: {country_name}")
                else:
                    print(f"Failed to fetch data for {country_code} in {region}: {response.status_code}")
            except Exception as e:
                print(f"Error processing country {country_code} in {region}: {e}")
            time.sleep(0.1)
    return data

def clean_religion_data(religions_str):
    main_religions = ['Catholic', 'Protestant', 'Jewish', 'Muslim', 'Hindu', 'Buddhist', 'Orthodox']
    extracted_religions = {religion: 0 for religion in main_religions}
    extracted_religions['Other/None'] = 0

    entries = religions_str.split('\n')
    for entry in entries:
        entry = entry.strip().lower()
        percentage = 0
        match = re.search(r'\b(\d{1,3}(?:\.\d+)?|\d+)%', entry)
        if match:
            percentage = float(match.group(1))

        for religion in main_religions:
            if religion.lower() in entry:
                extracted_religions[religion] += percentage
                break
        else:
            extracted_religions['Other/None'] += percentage

    extracted_religions = {k: v for k, v in extracted_religions.items() if v > 0}

    return extracted_religions

def get_all_country_data():
    indicators = {
        "SP.POP.TOTL": "Population",
        "NY.GDP.MKTP.CD": "GDP",
        "NY.GDP.MKTP.KD.ZG": "GDP Growth",
        "NY.GDP.PCAP.CD": "GDP Per Capita",
        "SL.UEM.TOTL.ZS": "Unemployment",
        "SP.POP.GROW": "Population Growth Rate",
    }
    worldometer_data = get_worldometer_data()
    life_expectancy_data = get_life_expectancy_data()
    factbook_data = get_factbook_data()
    currency_data = get_currency_info()
    all_data = []

    for country in pycountry.countries:
        country_name = country.name
        country_code = country.alpha_3
        country_key = country_name.strip().lower()

        country_data = {
            "Country": country_name,
            "Alpha-2": country.alpha_2,
            "Alpha-3": country.alpha_3,
            "Numeric Code": country.numeric,
        }

        if country_key in currency_data:
            country_data.update(currency_data[country_key])
        else:
            country_data["Currency Name"] = "N/A"
            country_data["Currency Code"] = "N/A"
            country_data["ISO Code"] = "N/A"

        world_bank_data = get_world_bank_data(country_code, indicators)
        defense_data = get_defense_expenditure(country_code)
        country_data.update(world_bank_data)
        country_data.update(defense_data)

        if country_key in worldometer_data:
            country_data.update(worldometer_data[country_key])
        if country_key in life_expectancy_data:
            country_data.update(life_expectancy_data[country_key])
        if country_key in factbook_data:
            country_data.update(factbook_data[country_key])

        all_data.append(country_data)
        time.sleep(0.5)

    for country_data in all_data:
        for key, value in country_data.items():
            if key not in ["Country", "Religions", "Alpha-2", "Alpha-3", "Numeric Code", "Currency Code", "Currency Name", "ISO Code"]:
                country_data[key] = clean_numeric_value(value)
        country_data['Religions'] = clean_religion_data(country_data.get('Religions', ''))

    return all_data


if __name__ == "__main__":
    print("Fetching data for all countries...")
    data = get_all_country_data()
    verified_data = [d for d in data if d.get("Country") and d.get("Population 2020")]
    print(f"Total countries processed: {len(verified_data)}")

    with open("country_data.json", "w") as f:
        json.dump(verified_data, f, indent=2)
    print("Data saved to 'country_data.json'.")

    start_year, current_year = get_year_range()
    years = range(start_year, current_year + 1)

    csv_fields = [
        "Country", "Currency Name", "Currency Code", "ISO Code",
    ]
    for indicator in ["Population", "GDP", "GDP Growth", "GDP Per Capita", "Unemployment", "Population Growth Rate", "Defense Expenditure (% of GDP)"]:
        csv_fields.extend([f"{indicator} {year}" for year in years])

    csv_fields.extend([
        "Yearly Change", "Net Change", "Density (P/Km²)", "Land Area (Km²)", "Migrants (net)",
        "Fertility Rate", "Median Age", "Urban Pop %", "World Share",
        "Age Structure (0-14)", "Age Structure (15-64)", "Age Structure (65+)",
        "GDP (PPP)", "GDP (Official Exchange Rate)", "Inflation Rate",
    ])

    gdp_composition_fields = set()
    for country in verified_data:
        gdp_composition_fields.update([k for k in country.keys() if k.startswith("GDP Composition - ")])
    csv_fields.extend(sorted(gdp_composition_fields))

    csv_fields.extend([
        "Life Expectancy (both)", "Life Expectancy (female)", "Life Expectancy (male)"
    ])

    csv_fields.extend([f"Religion {i+1}" for i in range(5)])
    csv_fields.extend([f"Religion {i+1} Percentage" for i in range(5)])

    with open("country_data.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for country in verified_data:
            row = {k: v for k, v in country.items() if k in csv_fields}
            for i, (religion, percentage) in enumerate(country['Religions'].items()):
                row[f"Religion {i+1}"] = religion.title()
                row[f"Religion {i+1} Percentage"] = percentage
                if i == 4:  
                    break
            writer.writerow(row)

    print("Data saved to 'country_data.csv'.")
