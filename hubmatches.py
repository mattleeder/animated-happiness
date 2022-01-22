import requests
from match import Match
from player import Player

class HubMatches:

    def __init__(self, hub_id, api_key):
        self.hub_id = hub_id
        self.api_key = api_key

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
        response = requests.get(url, headers = {"Authorization" : "Bearer " + self.api_key})
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

    def parse_match(self, match_id, player_dict, match_dict, insert = False):

        """
        Updates Player objects and creates Match objects for a specific match.
        """
        
        current_match = Match(match_id, self.api_key)
        current_match_data = current_match.match_stats()
        Player.parse_match_data(current_match_data, player_dict, insert)
        Match.full_parse(self.api_key, match_id, current_match_data, player_dict, match_dict)

    def full_match_loop(self, offset, limit, player_dict, match_dict):
        """
        Updates Player objects and creates Match objects for all matches.
        """
        
        match_id_list = self.get_full_match_list(offset, limit)
        
        for match_id in match_id_list[::-1]: # Which way?
            print(match_id)
            self.parse_match(match_id, player_dict, match_dict)

        return match_id_list
        
    def partial_match_loop(self, offset, limit, player_dict, match_dict, old_match_id_list):
        
        """
        Checks the hub matches and compares the IDs to matches already parsed to only get
        new match IDs, then parses through the new match IDs and adds them to the list.
        """
        
        old_length = len(old_match_id_list)
        match_id_list = self.get_full_match_list(offset, limit)
        new_length = len(match_id_list)
        length_diff = new_length - old_length
        
        new_match_id_list = match_id_list[:length_diff]
        new_match_id_list.reverse() #Reversing for insert to maintain order
        
        for match_id in new_match_id_list:
            print(match_id)
            self.parse_match(self.api_key, match_id, player_dict, match_dict, insert = True)

        return match_id_list