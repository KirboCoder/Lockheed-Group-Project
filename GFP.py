import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from time import sleep

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.76 Safari/537.36'
}

CATEGORIES = {
    'Manpower': {
        'total_population': 'https://www.globalfirepower.com/total-population-by-country.php',
        'available_manpower': 'https://www.globalfirepower.com/available-military-manpower.php',
        'fit_for_service': 'https://www.globalfirepower.com/manpower-fit-for-military-service.php',
        'reaching_military_age': 'https://www.globalfirepower.com/manpower-reaching-military-age-annually.php',
        'active_service': 'https://www.globalfirepower.com/active-military-manpower.php',
        'active_reserves': 'https://www.globalfirepower.com/active-reserve-military-manpower.php',
        'paramilitary': 'https://www.globalfirepower.com/manpower-paramilitary.php'
    },
    'Airpower': {
        'aircraft_total': 'https://www.globalfirepower.com/aircraft-total.php',
        'fighters_interceptors': 'https://www.globalfirepower.com/aircraft-total-fighters.php',
        'attack_strike': 'https://www.globalfirepower.com/aircraft-total-attack-types.php',
        'transports_fixed_wing': 'https://www.globalfirepower.com/aircraft-total-transports.php',
        'trainer_fleets': 'https://www.globalfirepower.com/aircraft-total-trainers.php',
        'special_mission': 'https://www.globalfirepower.com/aircraft-total-special-mission.php',
        'tanker_fleets': 'https://www.globalfirepower.com/aircraft-total-tanker-fleet.php',
        'helicopter_fleets': 'https://www.globalfirepower.com/aircraft-helicopters-total.php',
        'attack_helicopters': 'https://www.globalfirepower.com/aircraft-helicopters-attack.php'
    },
    'Land Forces': {
        'tank_strengths': 'https://www.globalfirepower.com/armor-tanks-total.php',
        'armored_fighting_vehicles': 'https://www.globalfirepower.com/armor-apc-total.php',
        'self_propelled_artillery': 'https://www.globalfirepower.com/armor-self-propelled-guns-total.php',
        'towed_artillery': 'https://www.globalfirepower.com/armor-towed-artillery-total.php',
        'rocket_projectors': 'https://www.globalfirepower.com/armor-mlrs-total.php'
    },
    'Naval Forces': {
        'naval_fleet_strength': 'https://www.globalfirepower.com/navy-ships.php',
        'fleet_tonnage_strength': 'https://www.globalfirepower.com/navy-force-by-tonnage.php',
        'aircraft_carriers': 'https://www.globalfirepower.com/navy-aircraft-carriers.php',
        'helicopter_carriers': 'https://www.globalfirepower.com/navy-helo-carriers.php',
        'submarines': 'https://www.globalfirepower.com/navy-submarines.php',
        'destroyers': 'https://www.globalfirepower.com/navy-destroyers.php',
        'frigates': 'https://www.globalfirepower.com/navy-frigates.php',
        'corvettes': 'https://www.globalfirepower.com/navy-corvettes.php',
        'coastal_patrol_craft': 'https://www.globalfirepower.com/navy-patrol-coastal-craft.php',
        'mine_warfare_craft': 'https://www.globalfirepower.com/navy-mine-warfare-craft.php'
    },
    'Finances': {
        'defense_budgets': 'https://www.globalfirepower.com/defense-spending-budget.php',
        'external_debt': 'https://www.globalfirepower.com/external-debt-by-country.php',
        'purchasing_power_parity': 'https://www.globalfirepower.com/purchasing-power-parity.php',
        'foreign_exchange_reserves': 'https://www.globalfirepower.com/reserves-of-foreign-exchang-and-gold.php'
    },
    'Logistics': {
        'airports': 'https://www.globalfirepower.com/major-serviceable-airports-by-country.php',
        'labor_force_strength': 'https://www.globalfirepower.com/labor-force-by-country.php',
        'major_ports_terminals': 'https://www.globalfirepower.com/major-ports-and-terminals.php',
        'merchant_marine_strength': 'https://www.globalfirepower.com/merchant-marine-strength-by-country.php',
        'railway_coverage': 'https://www.globalfirepower.com/railway-coverage.php',
        'roadway_coverage': 'https://www.globalfirepower.com/roadway-coverage.php'
    },
    'Natural Resources': {
        'oil_production': 'https://www.globalfirepower.com/oil-production-by-country.php',
        'oil_consumption': 'https://www.globalfirepower.com/oil-consumption-by-country.php',
        'proven_oil_reserves': 'https://www.globalfirepower.com/proven-oil-reserves-by-country.php',
        'natural_gas_production': 'https://www.globalfirepower.com/natural-gas-production-by-country.php',
        'natural_gas_consumption': 'https://www.globalfirepower.com/natural-gas-consumption-by-country.php',
        'proven_natural_gas_reserves': 'https://www.globalfirepower.com/proven-natural-gas-reserves-by-country.php',
        'coal_production': 'https://www.globalfirepower.com/coal-production-by-country.php',
        'coal_consumption': 'https://www.globalfirepower.com/coal-consumption-by-country.php',
        'proven_coal_reserves': 'https://www.globalfirepower.com/proven-coal-reserves-by-country.php'
    }
}

def parse_value(raw_value):
    """Enhanced value parser with unit conversion and currency handling"""
    if '$' in raw_value:
        raw_value = raw_value.replace('$', '').strip()
    
    # Extract numerical value and unit
    match = re.search(r'''
        ^               # Start of string
        (?:             # Non-capturing group
            \$?         # Optional dollar sign
            \s*         # Optional whitespace
        )?
        ([\d,.]+)       # Main numerical value (captured)
        \s*             # Optional whitespace
        ([A-Za-z.%/]*)  # Unit/description (captured)
        $               # End of string
    ''', raw_value, re.VERBOSE)

    if not match:
        return None
    
    value_str, unit = match.groups()
    value = value_str.replace(',', '')
    
    try:
        numerical_value = float(value)
    except ValueError:
        return None

    
    # Handle unit conversions
    unit_multipliers = {
        'B': 1e9, 'B Cu.M': 1e9, 'Billion': 1e9,
        'M': 1e6, 'Million': 1e6,
        'T': 1e12, 'Trillion': 1e12,
        '%': lambda x: x/100  # Convert percentage to decimal
    }
    
    if unit in unit_multipliers:
        if callable(unit_multipliers[unit]):
            return unit_multipliers[unit](value)
        return value * unit_multipliers[unit]
    
    return value

def scrape_category(url):
    """Improved value extraction with span depth handling"""
    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')
        data = {}
        
        country_blocks = soup.find_all('a', href=re.compile(r'country-military-strength-detail'))
        
        for block in country_blocks:
            try:
                country = block.find('div', class_='longFormName').span.text.strip()
                value_container = block.find('div', class_='valueContainer')
                
                # Improved value extraction logic
                if value_container:
                    # Get all nested spans
                    spans = value_container.find_all('span')
                    if spans:
                        # Use deepest nested span text
                        raw_value = spans[-1].text.strip()
                    else:
                        raw_value = value_container.text.strip()
                else:
                    raw_value = ''
                
                data[country] = parse_value(raw_value)
                
            except (AttributeError, ValueError) as e:
                continue
        
        return data
    
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return {}

def compile_dataset():
    master_df = pd.DataFrame()

    for category, subcats in CATEGORIES.items():
        print(f"\n{'='*40}\nScraping {category} Data\n{'='*40}")
        for subcat, url in subcats.items():
            print(f"-> {subcat.replace('_', ' ').title()}...")
            sleep
            data = scrape_category(url)
            temp_df = pd.DataFrame(list(data.items()), columns=['Country', subcat])
            
            if master_df.empty:
                master_df = temp_df
            else:
                master_df = pd.merge(master_df, temp_df, on='Country', how='outer')
            sleep(1)  # Rate limiting for servers to make sure they are good

    # Clean and sort data
    num_cols = master_df.columns[master_df.columns != 'Country']
    master_df[num_cols] = master_df[num_cols].apply(pd.to_numeric, errors='coerce')
    master_df = master_df.sort_values(by='Country').reset_index(drop=True)
    
    # Save to CSV
    master_df.to_csv('global_firepower_full_dataset.csv', index=False)
    print("\nDataset successfully saved to global_firepower_full_dataset.csv")

if __name__ == '__main__':
    compile_dataset()
