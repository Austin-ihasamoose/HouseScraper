from selenium import webdriver
import pandas as pd
import time
from bs4 import BeautifulSoup
import requests
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.disable(logging.CRITICAL)     # Use this to disable the logger

LOCATION = 'Your Location (city)'
BASE_URL = 'https://www.remax.ca/find-real-estate?address=' + LOCATION
BASE_FILTERS = {
    'BASE_FILTERS': '&commercial=false&commercialLease=false&vacantLand=false'
                    '&hotelResort=false&businessOpportunity=false&rentalsOnly=false'
                    '&commercialOnly=false&luxuryOnly=false&hasOpenHouse=false&hasVirtualOpenHouse=false'
                    '&parkingSpacesMin=&parkingSpacesMax=&commercialSqftMin=&commercialSqftMax='
                    '&unitsMin=&unitsMax=&storiesMin=&storiesMax=&totalAcresMin=&totalAcresMax='
                    '&Agriculture=false&Automotive=false&Construction=false&Grocery=false&Hospitality=false'
                    '&Hotel=false&Industrial=false&Manufacturing=false&Multi-Family=false'
                    '&Office=false&Professional=false&Restaurant=false&Retail=false&Service=false'
                    '&Transportation=false&Warehouse=false'
}


def to_hyperlink(link):
    return f'=HYPERLINK("{link}")'


def reformat_address(add):
    """
    :param add: Address as a split list from web object in soup
    :return: Formatted address string that deals with directional streets, i.e Street NW, Street SW
    """

    out_address = ''
    first_space = True
    logging.debug("In address: " + add)
    for char in add:
        count = 0
        if char.isdigit():
            out_address += str(char)
        elif char in 'Twp' and len(out_address) < 3:
            out_address += str(char)
        elif char in " -,":
            out_address += str(char)
        elif not char.islower() and out_address[-1] in " -":  # if char upper and last char is " -"
            out_address += str(char)
        elif not char.islower() and not out_address[-1] in " -" and first_space is True:
            out_address += ", " + str(char)
            first_space = False
        elif char.islower():
            out_address += str(char)
        elif not (char.islower() and (count == len(add))) or (char.isalpha() and (count == len(add))):
            out_address += str(char)

    logging.debug("Out address: " + out_address)
    return out_address


def process_all_pages(driver, price_min=None, price_max=None, beds_min=None, beds_max=None,
                      property_type=None, sqft_min=None, sqft_max=None, page_limit=0):
    """

    :param driver:          Webdriver to use
    :param price_min:       Integer value
    :param price_max:       Integer value
    :param beds_min:        Integer value
    :param beds_max:        Integer value
    :param property_type:   [house, condo, townhouse, land, duplex, cottage, other]
    :param sqft_min:        Integer value
    :param sqft_max:        Integer value
    :param page_limit:      Integer value. Defaults to max pages.
    :return:
    """
    global BASE_URL, BASE_FILTERS

    pr_min = '&priceMin='
    pr_max = '&priceMax='
    bd_min = '&bedsMin='
    bd_max = '&bedsMax='
    pr_type = '&house=false&townhouse=false&condo=false&rental=false&land=false' \
              '&farm=false&duplex=false&cottage=false&other=false'
    pr_words = ['house', 'townhouse', 'condo', 'rental', 'land', 'farm', 'duplex', 'cottage', 'other']

    filters = [pr_min, pr_max, bd_min, bd_max, pr_type]

    parameters = [price_min, price_max, beds_min, beds_max, property_type.lower(), sqft_min, sqft_max]
    page = 1
    url = BASE_URL + '&pageNumber=' + str(page) + BASE_FILTERS['BASE_FILTERS']
    pages_counting = True
    last_cycle = False

    for i in range(0, len(parameters)):
        logging.debug("Param: " + str(parameters[i]))
        if parameters[i] is not None:   # Populate URL
            pr_type_out = []            # This is to modify the property_type
            logging.debug("Param not none: " + str(parameters[i]))
            if any(x in str(parameters[i]) for x in pr_words):  # If any pr_word in property_types
                spl = pr_type.split('&')
                for f in spl:
                    logging.debug("f: " + f)
                    if parameters[i] in f and len(parameters[i]) == (len(f)-6):
                        f = '&' + parameters[i] + '=true'
                        pr_type_out.append(f)
                    else:
                        if len(f) > 1:  # To remove the initial blank list spacing of
                            logging.debug("F: " + f)
                            pr_type_out.append('&' + f)
                for pr_type in pr_type_out:
                    print("PR TYPE:" + pr_type)
                logging.debug("PR TYPE OUT: " + ''.join(pr_type_out))

            else:
                filters[i] = filters[i] + str(parameters[i])
                logging.debug(filters[i])

    while pages_counting is True and last_cycle is False:
        logging.debug("Page count: " + str(page))
        logging.debug("URL=" + str(url))
        driver.get(url + '&pageNumber=' + str(page))
        time.sleep(3)
        logging.debug("Current URL: " + driver.current_url)

        if int(page) == int(driver.current_url[-1]):
            if int(page) == int(page_limit):
                last_cycle = True
                logging.debug("Last cycle is true")
            logging.debug(int(page) == int(driver.current_url[-1]))
            print(driver.current_url)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            listing_data = soup.find_all("a", class_="listing-card_listingCard__G6M8g")
            process_page_listings(listing_data)
            page += 1
            url = BASE_URL + '&pageNumber=' + str(page)
            logging.debug("URL is now: " + url)
        else:
            pages_counting = False
            logging.debug("Page failed to go up in values. Finished processing.")

    return


def process_page_listings(data_list):
    """
    :param data_list: A list of HTML dictionaries based on process_listing's ind_listing on contextual page
    :return:
    """
    for each_listing in data_list:
        process_listing(each_listing)
        time.sleep(3)

    return


def process_listing(ind_listing):
    """
    Purpose: Process each listing individually so that we don't accidentally DDOS Remax's site
    :param ind_listing: A dictionary based on the HTML. i.e:
    <div class="listing-card_listingCardImage__XssW8"><div style="width: 100%; height: 100%;">
    <img alt="9022 153 Street" class="lazyload" sizes="382.22222222222223px" style="object-fit: cover; width: 100%; height: 100%;"/></div></div>
    :return: None
    """

    data = {}
    ind_listing = ind_listing['href']  # first link
    html = requests.get(ind_listing).text

    if html:
        soup2 = BeautifulSoup(html, 'html.parser')
        data['Price'] = soup2.find("div", class_="listing-summary_listPrice__PJawt").text
        data['Sq Footage'] = soup2.find_all("span", class_="listing-summary_propertyDetailValue__UOUcR")[2].text
        data['Bedroom(s)'] = soup2.find_all("span", class_="listing-summary_propertyDetailValue__UOUcR")[1].text
        data['Bathroom(s)'] = soup2.find_all("span", class_="listing-summary_propertyDetailValue__UOUcR")[0].text
        in_address = soup2.find("h1",
                                class_="listing-address_root__PP_Ky listing-summary_addressWrapper__ihFFk").text
        out_address = reformat_address(in_address)
        data['Address'] = out_address
        # data['Address'] = soup2.find("h1",
        #                               class_="listing-address_root__PP_Ky listing-summary_addressWrapper__ihFFk").text
        data['URL'] = ind_listing
        # data['Date Listed']=soup2.find("span",class_="listing-summary_propertyDetailValue__UOUcR").text
        # data['Garage']=soup2.find("span",class_="listing-summary_propertyDetailValue__UOUcR").text
        # data['Listing Link']=soup2.find("span",class_="listing-summary_propertyDetailValue__UOUcR").text
        # data['MLS #']=soup2.find("span",class_="listing-summary_propertyDetailValue__UOUcR").text
        # data['Renovated Keyword']=soup2.find("span",class_="listing-summary_propertyDetailValue__UOUcR").text
        # data['Property Type']=soup2.find("span",class_="listing-summary_propertyDetailValue__UOUcR").text
        fstring = (
            f"\nPrice: {data['Price']}"
            f"\nSq Ft:  {data['Sq Footage']}"
            f" \nBedrooms:  {data['Bedroom(s)']}"
            f" \nBaths:  {data['Bathroom(s)']}"
            f" \nAddress: {data['Address']}"
            f" \nLink:  {data['URL']}"
        )
        logging.debug(fstring)

        index = len(df)
        for key in data:
            if data[key] is None \
                    or data[key] == '0' \
                    or data[key] == '':
                logging.debug("data[key] = " + data[key])
                df.at[index, key] = "N/A"

            if data[key].startswith("http"):
                df.at[index, key] = data[key]
                df.at[index, 'Hyperlink'] = to_hyperlink(data[key])
            else:
                df.at[index, key] = data[key]

    else:
        driver.quit()
        raise Exception("Error reaching request")

    return


if __name__ == '__main__':
    logging.debug("Start")
    df = pd.DataFrame()
    driver = webdriver.Firefox()
    process_all_pages(driver, price_max=430000, property_type='house', page_limit=0)
    df.to_excel("Output.xlsx", index=False)
    # df.to_sql()
    driver.quit()
    logging.debug("End")
