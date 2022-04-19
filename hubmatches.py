import requests
from match import Match
from player import Player

import logging
from rq import get_current_job

import os
import cProfile, pstats, io
from pstats import SortKey

import aiohttp
import asyncio
import time

api_key = os.environ["API_KEY"]

async def get_match(session, url):
    async with session.get(url, headers = {"Authorization" : "Bearer " + api_key}) as resp:
        match = await resp.json()
        try:
            return match["rounds"][0]
        except:
            return None

async def match_loop(match_list):

    async with aiohttp.ClientSession() as session:

        tasks = []
        for match_id in match_list:
            url = f"https://open.faceit.com/data/v4/matches/{match_id}/stats"
            tasks.append(asyncio.ensure_future(get_match(session, url)))

        match_data = await asyncio.gather(*tasks)
        for match in match_data:
            try:
                print(match["match_id"])
            except TypeError:
                print("404")
        print(len(match_data))
    
    return match_data

class HubMatches:

    def __init__(self, hub_id, player_json = None, match_json = None):
        self.hub_id = hub_id
        self.player_json = player_json
        self.match_json = match_json
        if player_json is None:
            self.player_json = {}
        if match_json is None:
            self.match_json = {}

    def _limited_match_list(self, offset, limit):
        """
        Returns a list containing up to 200 match IDs after the offset from a specified Faceit Hub.

        Paramters
        ---------

        offset : int
                The number of the earliest match to fetch. 
        limit : int
                The number of matches to fetch per api call. Maximum is 200.

        Returns
        -------
        
        match_id_list : list
                A list containing the IDs of the matches.
        """

        url = f"https://open.faceit.com/data/v4/hubs/{self.hub_id}/matches?type=past&offset={offset}&limit={limit}"
        response = requests.get(url, headers = {"Authorization" : "Bearer " + api_key})
        data = response.json()
        
        match_id_list = []
        
        for item in data["items"]:
            match_id_list.append(item["match_id"])
        return match_id_list

    def get_full_match_list(self, offset, limit):
        """
        Returns a list containing all Match IDs from a specified Faceit Hub.

        Paramters
        ---------

        offset : int
                The number of the earliest match to fetch
        actual_limit : int
                Text

        Returns
        -------

        full_match_list : list
                List containing all Match IDs from the specified Faceit Hub.
        """
        
        full_match_list = []
        
        # Could this be removed?
        while True:
            
            if limit <= 100:
                match_id_list = self._limited_match_list(offset, limit)
                full_match_list.extend(match_id_list)
                break
                
            match_id_list = self._limited_match_list(offset, 100)
            
            if len(match_id_list) == 0:
                break

            offset += 100
            limit -= 100
            full_match_list.extend(match_id_list)

            
        return full_match_list

    def parse_match(self, match_id, match_data):

        """
        Updates Player objects and creates Match objects for a specific match.
        """
        
        current_match = Match(match_id)
        # current_match_data = current_match.match_stats()
        Player.parse_match_data(match_id, match_data, self.player_json)
        Match.full_parse(match_id, match_data, self.match_json, self.player_json)

    def full_match_loop(self, offset, limit):
        """
        Updates Player objects and creates Match objects for all matches.
        """
        job = get_current_job()
        job.meta["progress"] = job.meta.get("progress", 0)
        job.save_meta()
     
        match_id_list = self.get_full_match_list(offset, limit)
        match_data = asyncio.run(match_loop(match_id_list))

        logging.debug(match_data)

        job.meta["length"] = len(match_id_list)
        job.save_meta()
        
        for match_id, data in zip(match_id_list[::-1], match_data[::-1]): # Which way?
            logging.debug(match_id)
            self.parse_match(match_id, data)
            job.meta["progress"] += 1
            job.save_meta()

        return match_id_list
        
    def partial_match_loop(self, offset, limit, old_match_id_list):
        
        """
        Checks the hub matches and compares the IDs to matches already parsed to only get
        new match IDs, then parses through the new match IDs and adds them to the list.
        """

        logging.debug("Partial Called")
        
        old_length = len(old_match_id_list)
        match_id_list = self.get_full_match_list(offset, limit)
        new_length = len(match_id_list)
        length_diff = new_length - old_length
        
        new_match_id_list = match_id_list[:length_diff]
        new_match_id_list.reverse() # Reversing to maintain order, is this right?
        new_match_data = asyncio.run(match_loop(new_match_id_list))
        
        for match_id, data in zip(new_match_id_list, new_match_data):
            logging.debug(match_id)
            self.parse_match(match_id, data)

        return match_id_list