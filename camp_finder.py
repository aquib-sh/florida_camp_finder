#Author : Shaikh Aquib
#Date   : June 2021

from os import stat
import time
import requests
import bs4
import pandas
import schedule
import config
from bot import BotMaker

class CampFinder:
    """CampFinder
    Finds camps around florida, if a camp seat is available then alerts user on Telegram.

    Attributes
    ---------
    bot:bot.BotMaker
        BotMaker object which opens up the browser instance with the help of selenium.

    df:pandas.DataFrame
        Pandas DataFrame containing the data from input .xlsx file.

    xpaths:dict
        Dictionary containing the names of elements mapped to their xpaths.
    """

    def __init__(self):

        self.xpaths = {
            "input_park"         : '//input[@id="txtCityParkSearch"]',
            "input_arrival_date" : '//input[@id="mainContent_SearchUnitAvailbity_txtArrivalDate"]',
            "select_stay_length" : '//select[@id="ddlHomeNights"]',
            "option_stay_length" : '//option[@value="{}"]',
            "btn_search"         : '//a[@onclick="SearchPlaceDateNightValues();"]',
        }
        print("[+] Initializing bot...")
        self.bot = BotMaker(browser=config.browser, behead=True)
        wait = self.bot.create_driver_wait(20)

        print("[+] Loading Website...")
        self.bot.move(config.website)
        time.sleep(config.website_load_time)
        self.bot.wait_until_found_xpath(wait, self.xpaths['input_park'])
        self.bot.wait_until_found_xpath(wait, self.xpaths['input_arrival_date'])
        self.bot.wait_until_found_xpath(wait, self.xpaths['btn_search'])
        self.bot.execute_script("window.stop();")

        print("[+] Loading data from input file...")
        self.df = pandas.read_csv(config.input_file)


    def get_input_df(self) -> pandas.core.frame.DataFrame:
        """Returns DataFrame of the input file."""
        return self.df


    def prepare_soup(self) -> bs4.BeautifulSoup:
        """Returns BeautifulSoup object of the current webpage."""
        return bs4.BeautifulSoup(self.bot.page_source(), "lxml")


    def search(self, park:str, arrival_date:str, stay:int):
        """Searches for a park based on the information provided.

        Parameters
        ----------
        park : str
            Park name to search

        arrival_date : str
            Arrival date in format mm/dd/yyyy

        stay : int
            Days for which camp stay is required (stay_length)
        """
        self.bot.get_element(self.xpaths['input_park']).clear()
        self.bot.get_element(self.xpaths['input_park']).send_keys(park)
        time.sleep(2)
        self.bot.get_element_by_css_selector('#ui-id-1').click()
        self.bot.get_element(self.xpaths['input_arrival_date']).send_keys(arrival_date)
        self.bot.get_element_by_css_selector(f'#ddlNightsSearchUnitAvailbity > option:nth-child({stay})').click()
        self.bot.get_element(self.xpaths['btn_search']).click()


    def get_data_rows(self, soup:bs4.BeautifulSoup) -> list:
        """Returns the rows of data from the table which has facility, unit_type and availibility status.
        
        Parameters
        ----------
        soup : bs4.BeautifulSoup
            Source of the page to get elements from.

        Attributes
        ----------
        table_box : bs4.element.Tag
            Source of the table containing data about facility, units and availibility.

        rows : list
            Source of all the <tr> present in above table except first one.

        Returns
        -------
        rows : list

        """
        table_box = soup.find("div", {"class": "table_data_box"})
        rows = table_box.find_all("tr")
        rows = rows[1:]

        return rows


    def get_facility(self, row:bs4.element.Tag) -> str:
        """Returns the facility data from the table row.
        
        Parameters
        ----------
        row : bs4.element.Tag
            individual row from data rows in table.

        Attributes
        ----------
        facility : bs4.element.Tag
            Facility data from row.
 
        """
        facility = row.find("td").find("div").find("span")

        if facility : return facility.text.strip()
        return "N/A"


    def get_unit_type(self, row:bs4.element.Tag) -> str:
        """Returns the facility data from the table row.
        
        Parameters
        ----------
        row : bs4.element.Tag
            individual row from data rows in table.

        Attributes
        ----------
        temp : bs4.element.Tag
            Row within the individual row in table, containing unit_type and availability data.

        unit_type : str
            Unit type of the current available seat in camp.
 
        """
        temp = row.find("td").find_next_sibling().find("div", {"class": "row"})
        if not temp : temp = row.find("td").find("div", {"class":"row"})
        
        unit_type = temp.find("img").find_parent().text.strip()
        return unit_type


    def is_seat_available(self, row:bs4.element.Tag) -> bool:
        """Checks if the seat is available for current facility and unit type in park.
        
        Parameters
        ----------
        row : bs4.element.Tag
            individual row from data rows in table.

        Attributes
        ----------
        temp : bs4.element.Tag
            Row within the individual row in table, containing unit_type and availability data.

        unit_type : str
            Unit type of the current available seat in camp.

        """
        temp = row.find("td").find_next_sibling().find("div", {"class": "row"})
        if not temp : temp = row.find("td").find("div", {"class":"row"})

        avail = temp.find("div", {"class": "btnFacilityclick"}).text.strip()
        if avail == "Reserve" : return True            
        return False


    def get_chat_id (self, token:str) -> tuple :
        """ Returns the chat_id from the latest message. 
        
        Parameters
        ----------
        token : str
            Token for using the Telegram bot.

        Returns
        -------
        Tuple containing chat_id and user_id of the last person who sent msg.

        """
        method_update="getUpdates"
        response1 = requests.post(
            url='https://api.telegram.org/bot{0}/{1}'.format(token, method_update)

        )
        if response1.status_code != 200:
            print("[-] Error in getting the chat_id")
            print("[-] Make sure you have sent /start msg to bot")
            return None
        data = response1.json()
        # chat_id will be extracted always from the latest person
        # who sent the message
        chat_id = data['result'][-1]['message']['chat']['id']
        user = data['result'][-1]['message']['chat']['first_name']

        return (chat_id, user)


    def send_msg (self, token, chat_id, msg) :
        """ Sends message by chat_id. """

        method_send ="sendMessage"
        r = requests.post(
            url='https://api.telegram.org/bot{0}/{1}'.format(token, method_send),
            data={'chat_id': chat_id, 'text': msg}
        )
        if r.status_code != 200:
            print("[-] Error sending message")
        return r.status_code


    def refresh_page (self) :
        """ Refreshes the page. """
        self.bot.driver.refresh()


    def shutdown(self):
        self.bot.shutdown()


if __name__ == "__main__":
    finder = CampFinder()
    chat_id, user = finder.get_chat_id(token=config.token)

    def job():
        print("[+] Checking availibility...")
        for i in range(0, len(finder.df)):
            park = finder.df.iloc[i]['park']
            date = finder.df.iloc[i]['date']
            stay = finder.df.iloc[i]['no of nights']

            # Capitalize each word of the park
            words = park.split()
            temp = ""
            for word in words:
                if words.index(word) == (len(words)-1):
                    temp += word.capitalize()
                else:
                    temp += (word.capitalize() + " ")
            park = temp
            del temp

            finder.search(park, date, int(stay))

            # Parse the HTML Source Code and find values
            soup = finder.prepare_soup()

            rows = finder.get_data_rows(soup)

            for row in rows:
                facility  = finder.get_facility(row)
                unit_type = finder.get_unit_type(row)
                if finder.is_seat_available(row):
                    statement = f"{park}\n\tFacility : {facility}\n\tUnit Type : {unit_type}\n\tFrom {date}\nis AVAILABLE for {stay} nights"
                    print(statement)
                    finder.send_msg(config.token, chat_id, statement)
                    print(f"\t-> Message sent to '{user}'")
                    print("-----"*10)
                    print("-----"*10)

    job()
    schedule.every(config.runtime_interval_mins).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)