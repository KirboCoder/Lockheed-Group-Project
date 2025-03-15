import requests
from bs4 import BeautifulSoup
import os
import time

def download_image(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded: {filename}")
    else:
        print(f"Failed to download: {filename}")

def get_country_maps(country_name, url_name):
    base_url = "https://srv1.worldometers.info"
    country_dir = os.path.join('country_maps', country_name)
    if not os.path.exists(country_dir):
        os.makedirs(country_dir)

    map_types = ['physical', 'political']
    
    for map_type in map_types:
        # Try both .gif and .png extensions
        for extension in ['gif', 'png']:
            try:
                img_url = f"{base_url}/img/maps/{url_name}_{map_type}_map.{extension}"
                filename = os.path.join(country_dir, f"{country_name}_{map_type}_map.{extension}")
                
                response = requests.get(img_url)
                if response.status_code == 200:
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    print(f"Downloaded: {filename}")
                    break  # Skip trying other extensions if successful
                
            except requests.exceptions.RequestException as e:
                print(f"Error downloading {map_type} map for {country_name}: {e}")
                continue

    print(f"Processed {country_name}")


def main():
    countries = [
        ("Afghanistan", "afghanistan"),
        ("Albania", "albania"),
        ("Algeria", "algeria"),
        ("Andorra", "andorra"),
        ("Angola", "angola"),
        ("Antigua and Barbuda", "antigua"),
        ("Argentina", "argentina"),
        ("Armenia", "armenia"),
        ("Australia", "australia"),
        ("Austria", "austria"),
        ("Azerbaijan", "azerbaijan"),
        ("Bahamas", "bahamas"),
        ("Bahrain", "bahrain"),
        ("Bangladesh", "bangladesh"),
        ("Barbados", "barbados"),
        ("Belarus", "belarus"),
        ("Belgium", "belgium"),
        ("Belize", "belize"),
        ("Benin", "benin"),
        ("Bhutan", "bhutan"),
        ("Bolivia", "bolivia"),
        ("Bosnia and Herzegovina", "bosnia"),
        ("Botswana", "botswana"),
        ("Brazil", "brazil"),
        ("Brunei", "brunei"),
        ("Bulgaria", "bulgaria"),
        ("Burkina Faso", "burkina"),
        ("Burundi", "burundi"),
        ("Cabo Verde", "cape-verde"),
        ("Cambodia", "cambodia"),
        ("Cameroon", "cameroon"),
        ("Canada", "canada"),
        ("Central African Republic", "central-african-republic"),
        ("Chad", "chad"),
        ("Chile", "chile"),
        ("China", "china"),
        ("Colombia", "colombia"),
        ("Comoros", "comoros"),
        ("Congo", "congo"),
        ("Costa Rica", "costa-rica"),
        ("Croatia", "croatia"),
        ("Cuba", "cuba"),
        ("Cyprus", "cyprus"),
        ("Czech Republic", "czech-republic"),
        ("Côte d'Ivoire", "cote-d-ivoire"),
        ("Denmark", "denmark"),
        ("Djibouti", "djibouti"),
        ("Dominica", "dominica"),
        ("Dominican Republic", "dominican-republic"),
        ("DR Congo", "democratic-republic-of-the-congo"),
        ("Ecuador", "ecuador"),
        ("Egypt", "egypt"),
        ("El Salvador", "el-salvador"),
        ("Equatorial Guinea", "equatorial-guinea"),
        ("Eritrea", "eritrea"),
        ("Estonia", "estonia"),
        ("Eswatini", "swaziland"),
        ("Ethiopia", "ethiopia"),
        ("Fiji", "fiji"),
        ("Finland", "finland"),
        ("France", "france"),
        ("Gabon", "gabon"),
        ("Gambia", "gambia"),
        ("Georgia", "georgia"),
        ("Germany", "germany"),
        ("Ghana", "ghana"),
        ("Greece", "greece"),
        ("Grenada", "grenada"),
        ("Guatemala", "guatemala"),
        ("Guinea", "guinea"),
        ("Guinea-Bissau", "guinea-bissau"),
        ("Guyana", "guyana"),
        ("Haiti", "haiti"),
        ("Holy See", "vatican-city"),
        ("Honduras", "honduras"),
        ("Hungary", "hungary"),
        ("Iceland", "iceland"),
        ("India", "india"),
        ("Indonesia", "indonesia"),
        ("Iran", "iran"),
        ("Iraq", "iraq"),
        ("Ireland", "ireland"),
        ("Israel", "israel"),
        ("Italy", "italy"),
        ("Jamaica", "jamaica"),
        ("Japan", "japan"),
        ("Jordan", "jordan"),
        ("Kazakhstan", "kazakhstan"),
        ("Kenya", "kenya"),
        ("Kiribati", "kiribati"),
        ("Kuwait", "kuwait"),
        ("Kyrgyzstan", "kyrgyzstan"),
        ("Laos", "laos"),
        ("Latvia", "latvia"),
        ("Lebanon", "lebanon"),
        ("Lesotho", "lesotho"),
        ("Liberia", "liberia"),
        ("Libya", "libya"),
        ("Liechtenstein", "liechtenstein"),
        ("Lithuania", "lithuania"),
        ("Luxembourg", "luxembourg"),
        ("Madagascar", "madagascar"),
        ("Malawi", "malawi"),
        ("Malaysia", "malaysia"),
        ("Maldives", "maldives"),
        ("Mali", "mali"),
        ("Malta", "malta"),
        ("Marshall Islands", "marshall-islands"),
        ("Mauritania", "mauritania"),
        ("Mauritius", "mauritius"),
        ("Mexico", "mexico"),
        ("Micronesia", "micronesia"),
        ("Moldova", "moldova"),
        ("Monaco", "monaco"),
        ("Mongolia", "mongolia"),
        ("Montenegro", "montenegro"),
        ("Morocco", "morocco"),
        ("Mozambique", "mozambique"),
        ("Myanmar", "myanmar"),
        ("Namibia", "namibia"),
        ("Nauru", "nauru"),
        ("Nepal", "nepal"),
        ("Netherlands", "netherlands"),
        ("New Zealand", "new-zealand"),
        ("Nicaragua", "nicaragua"),
        ("Niger", "niger"),
        ("Nigeria", "nigeria"),
        ("North Korea", "north-korea"),
        ("North Macedonia", "macedonia"),
        ("Norway", "norway"),
        ("Oman", "oman"),
        ("Pakistan", "pakistan"),
        ("Palau", "palau"),
        ("Panama", "panama"),
        ("Papua New Guinea", "papua-new-guinea"),
        ("Paraguay", "paraguay"),
        ("Peru", "peru"),
        ("Philippines", "philippines"),
        ("Poland", "poland"),
        ("Portugal", "portugal"),
        ("Qatar", "qatar"),
        ("Romania", "romania"),
        ("Russia", "russia"),
        ("Rwanda", "rwanda"),
        ("Saint Kitts and Nevis", "saint-kitts-and-nevis"),
        ("Saint Lucia", "saint-lucia"),
        ("Samoa", "samoa"),
        ("San Marino", "san-marino"),
        ("Sao Tome and Principe", "sao-tome-and-principe"),
        ("Saudi Arabia", "saudi-arabia"),
        ("Senegal", "senegal"),
        ("Serbia", "serbia"),
        ("Seychelles", "seychelles"),
        ("Sierra Leone", "sierra-leone"),
        ("Singapore", "singapore"),
        ("Slovakia", "slovakia"),
        ("Slovenia", "slovenia"),
        ("Solomon Islands", "solomon-islands"),
        ("Somalia", "somalia"),
        ("South Africa", "south-africa"),
        ("South Korea", "south-korea"),
        ("South Sudan", "south-sudan"),
        ("Spain", "spain"),
        ("Sri Lanka", "sri-lanka"),
        ("St. Vincent and Grenadines", "saint-vincent-and-the-grenadines"),
        ("State of Palestine", "palestine"),
        ("Sudan", "sudan"),
        ("Suriname", "suriname"),
        ("Sweden", "sweden"),
        ("Switzerland", "switzerland"),
        ("Syria", "syria"),
        ("Tajikistan", "tajikistan"),
        ("Tanzania", "tanzania"),
        ("Thailand", "thailand"),
        ("Timor-Leste", "east-timor"),
        ("Togo", "togo"),
        ("Tonga", "tonga"),
        ("Trinidad and Tobago", "trinidad-and-tobago"),
        ("Tunisia", "tunisia"),
        ("Turkey", "turkey"),
        ("Turkmenistan", "turkmenistan"),
        ("Tuvalu", "tuvalu"),
        ("Uganda", "uganda"),
        ("Ukraine", "ukraine"),
        ("United Arab Emirates", "united-arab-emirates"),
        ("United Kingdom", "united-kingdom"),
        ("United States", "united-states"),
        ("Uruguay", "uruguay"),
        ("Uzbekistan", "uzbekistan"),
        ("Vanuatu", "vanuatu"),
        ("Venezuela", "venezuela"),
        ("Vietnam", "vietnam"),
        ("Yemen", "yemen"),
        ("Zambia", "zambia"),
        ("Zimbabwe", "zimbabwe")
    ]

    for country_name, url_name in countries:
        get_country_maps(country_name, url_name)
        time.sleep(1)  # Be respectful to the server

    print("All country maps have been processed.")

if __name__ == "__main__":
    main()
