import csv
import os
from dotenv import load_dotenv
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

URL = "https://www.airlinemogul.com/index.php"
URL_WORLD = "https://www.airlinemogul.com/select_world.php?id="
URL_ROUTES = "https://www.airlinemogul.com/research_route.php"

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

def setup_driver():
    option = webdriver.ChromeOptions()
    chrome_prefs = {}
    option.experimental_options["prefs"] = chrome_prefs
    chrome_prefs["profile.default_content_settings"] = {"images": 2}
    chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}
    driver = webdriver.Chrome(options=option)
    return driver


class Client:
    def __init__(self):
        self.urls = {
            "home": URL,
            "world": URL_WORLD,
            "routes": URL_ROUTES
        }
        self.driver = setup_driver()
        self.departure = None
        self.arrival = None
        self.departure_continent = None
        self.arrival_continent = None
        self.distances = []

    def login(self, username, password):
        self.driver.get(URL)
        username_input = self.driver.find_element_by_name("username")
        password_input = self.driver.find_element_by_name("password")
        login_button = self.driver.find_element_by_name('Login')
        username_input.clear()
        password_input.clear()
        username_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()

    def select_world(self, world_id):
        self.world = world_id
        world_url = self.urls["world"] + world_id
        self.driver.get(world_url)
        text = "PW#{}. aereo_2018".format(world_id)
        xpath = '//h2[text()="{}"]'.format(text)
        message = "World {} successfully selected!".format(world_id)
        self.wait_until_loaded(xpath, message)

    def go_to_routes(self):
        self.driver.get(self.urls["routes"])

    def wait_until_loaded(self, xpath, message="Correctly loaded"):
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, xpath)))
            print(message)
        except TimeoutException:
            print("Time exceeded! (still waiting for page to load)")

    def wait_until_dissapears(self, xpath):
        try:
            WebDriverWait(self.driver, 1
                          ).until(EC.presence_of_element_located((By.XPATH, xpath)))

            # then wait for the element to disappear
            WebDriverWait(self.driver, 5
                          ).until_not(EC.presence_of_element_located((By.XPATH, xpath)))
        except TimeoutException:
            print("Time exceeded!")

    def continent_selector(self, field="depart"):
        cont_id = "{}_sel".format(field)
        return Select(self.driver.find_element_by_id(cont_id))

    def airport_selector(self, field="depart"):
        apt_id = "{}_sel_apt".format(field)
        return Select(self.driver.find_element_by_id(apt_id))

    def choose_continent(self, field="depart", continent="All"):
        xpath = "//select[@id='{}_sel']/option[text()='{}']".format(
            field, continent)        
        self.wait_until_loaded(xpath)
        if field == "depart":
            selector = self.continent_selector("depart")
            selector.select_by_visible_text(continent)
            self.departure_continent = continent
        elif field == "arrive":
            selector = self.continent_selector("arrive")
            selector.select_by_visible_text(continent)
            self.arrival_continent = continent
        xpath = "//select[@id='{}_sel']/option[text()='{}']".format(
            field, "Loading...")
        self.wait_until_dissapears(xpath)
        self.driver.implicitly_wait(2)
        print("Selected {} continent: {}".format(field, continent))

    def choose_airport(self, airport, field="depart"):
        xpath = "//select[@id='{}_sel_apt']/option[@value='{}']".format(
            field, airport["value"])
        message = "{} airport options loaded".format(
            "Departure" if field == "depart" else "Arrival")
        self.wait_until_loaded(xpath, message)
        if field == "depart":
            selector = self.airport_selector("depart")
            selector.select_by_value(airport["value"])
            self.departure = airport["value"]
        elif field == "arrive":
            selector = self.airport_selector("arrive")
            selector.select_by_value(airport["value"])
            self.arrival = airport["value"]
        element = self.driver.find_element_by_xpath(xpath)
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_selected((element)))
        print("Selected {} airport: {}".format(field, airport["text"]))            

    def airport_list(self, field="depart"):
        selector = self.airport_selector(field)
        options = selector.options
        return list(map(lambda x: {"value": x.get_attribute(
            'value'), "text": x.text}, options))

    def research_route(self):
        depart_xpath = "//select[@id='depart_sel_apt']/option[@value='{}']".format(
            self.departure)
        arrive_xpath = "//select[@id='arrive_sel_apt']/option[@value='{}']".format(
            self.arrival)

        try:
            depart_element = self.driver.find_element_by_xpath(depart_xpath)
            arrive_element = self.driver.find_element_by_xpath(arrive_xpath)
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_selected((depart_element)))
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_selected((arrive_element)))
        except TimeoutException:
            print("Time exceeded!")

        xpath = "//input[@name='submit']"
        submit_btn = self.driver.find_element_by_xpath(xpath)
        submit_btn.click()

        xpath = "//td[text()='Route Details']"
        message = "Route details loaded"
        self.wait_until_loaded(xpath, message)

    def save_distance(self, arrival):
        xpath = "//b[text()='Distance']/../following-sibling::td"
        distance_elem = self.driver.find_element_by_xpath(xpath)
        distance = distance_elem.text.replace('"', '')
        data = {
            "airport": arrival['text'].strip(),
            "id": arrival['value'],
            "distance": distance,
            "departure_continent": self.departure_continent,
            "arrival_continent": self.arrival_continent
        }
        print("Saving data: {}".format(data))
        self.distances.append(data)

    def dump_to_file(self, filename):
        with open('{}.csv'.format(filename), mode='w', encoding='utf-8') as csv_file:
            fieldnames = ['airport', 'id', 'distance',
                          'departure_continent', 'arrival_continent']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.distances:
                writer.writerow(row)

#  Program


client = Client()
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
client.login(username, password)
world_id = os.getenv("WORLD")
client.select_world(world_id)
client.go_to_routes()

client.choose_continent("depart", "Bases")
departures = client.airport_list("depart")
base_departure = departures[-1]

client.choose_airport(base_departure, "depart")

## Select airports at Central America

client.choose_continent("arrive", "Central America")
arrivals = client.airport_list("arrive")

count = 0
for arrival in arrivals:
    if arrival["value"] == "x":
        continue
    client.choose_airport(arrival, "arrive")
    client.research_route()
    client.save_distance(arrival)
    print("==========================")
    count += 1
    if count > 1:
        break

## Select airports at South America

client.choose_continent("arrive", "South America")
arrivals = client.airport_list("arrive")

count = 0
for arrival in arrivals:
    if arrival["value"] == "x":
        continue
    client.choose_airport(arrival, "arrive")
    client.research_route()
    client.save_distance(arrival)
    count += 1
    print("==========================")
    if count > 1:
        break

## Save results

client.dump_to_file("extracted_distances")
