import requests
import json
import csv
import time
import re
from bs4 import BeautifulSoup
import pycountry

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

def get_world_bank_data(country_code, indicators):
    base_url = "http://api.worldbank.org/v2"
    data = {}
    try:
        for indicator, key in indicators.items():
            response = requests.get(f"{base_url}/country/{country_code}/indicator/{indicator}?format=json")
            if response.status_code == 200:
                result = response.json()
                if len(result) > 1 and result[1]:
                    data[key] = result[1][0].get("value")
                else:
                    data[key] = None
    except Exception as e:
        print(f"World Bank API error: {e}")
    return data

def get_pycountry_data():
    country_data = []
    for country in pycountry.countries:
        country_data.append({
            'name': {'common': country.name},
            'cca3': country.alpha_3
        })
    return country_data

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

    # Split the input string and iterate through each entry
    entries = religions_str.split('\n')
    for entry in entries:
        entry = entry.strip().lower()
        percentage = 0
        match = re.search(r'\b(\d{1,3}(?:\.\d+)?|\d+)%', entry)
        if match:
            percentage = float(match.group(1))
        
        # Check for main religions
        for religion in main_religions:
            if religion.lower() in entry:
                extracted_religions[religion] += percentage
                break
        else:
            # If no main religion is found, add to Other/None
            extracted_religions['Other/None'] += percentage

    # Remove religions with 0 percentage
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
    pycountry_data = get_pycountry_data()
    worldometer_data = get_worldometer_data()
    life_expectancy_data = get_life_expectancy_data()
    factbook_data = get_factbook_data()
    all_data = []
    for country in pycountry_data:
        country_name = country['name']['common']
        country_code = country['cca3']
        country_key = country_name.strip().lower()
        country_data = {
            "Country": country_name,
        }
        world_bank_data = get_world_bank_data(country_code, indicators)
        country_data.update(world_bank_data)
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
            if key not in ["Country", "Religions"]:
                country_data[key] = clean_numeric_value(value)
        country_data['Religions'] = clean_religion_data(country_data.get('Religions', ''))

    return all_data

if __name__ == "__main__":
    print("Fetching data for all countries...")
    data = get_all_country_data()
    verified_data = [d for d in data if d.get("Country") and d.get("Population")]
    print(f"Total countries processed: {len(verified_data)}")

    with open("country_data.json", "w") as f:
        json.dump(verified_data, f, indent=2)
    print("Data saved to 'country_data.json'.")

    csv_fields = [
        "Country", "Population", "GDP", "GDP Growth", "GDP Per Capita",
        "Unemployment", "Population Growth Rate", "Yearly Change", "Net Change",
        "Density (P/Km²)", "Land Area (Km²)", "Migrants (net)", "Fertility Rate",
        "Median Age", "Urban Pop %", "World Share", "Age Structure (0-14)",
        "Age Structure (15-64)", "Age Structure (65+)", "GDP (PPP)",
        "GDP Growth Rate", "GDP (Official Exchange Rate)", "Inflation Rate",
        "GDP Composition - Agriculture", "GDP Composition - Industry",
        "GDP Composition - Services", "Life Expectancy (both)",
        "Life Expectancy (female)", "Life Expectancy (male)"
    ]

    main_religions = ['Catholic', 'Protestant', 'Jewish', 'Muslim', 'Hindu', 'Buddhist', 'Orthodox', 'Other/None']
    csv_fields.extend(main_religions)

    with open("country_data.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for country in verified_data:
            row = {k: v for k, v in country.items() if k in csv_fields and k != "Religions"}
            for religion in main_religions:
                row[religion] = country['Religions'].get(religion, 0)
            writer.writerow(row)

    print("Data saved to 'country_data.csv'.")