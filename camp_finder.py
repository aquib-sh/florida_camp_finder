#Author : Shaikh Aquib
#Date   : June 2021

import config
from bot import BotMaker

class CampFinder:
    """CampFinder

    Finds camps around florida, if a camp seat is availble then alerts user on Telegram
    """
    def __init__(self):
        self.bot = BotMaker(browser=config.browser)
        self.bot.move(config.website)
        self.xpaths = {}
