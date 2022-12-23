import aiohttp
import asyncio
from elo import Elo
import logging
import os
import requests
from rq import get_current_job
from typing import Dict, List, Union
import ujson

# player_json takes the form
# player_id : {
#     "Match ID" : List[str],
#     "Number of Rounds" : List[int],
#     "Map" : List[str],
#     "Deaths" : List[int],
#     "K/R Ratio" : List[Union[float, int]],
#     "MVPs" : List[int],
#     "Headshots" : List[int],
#     "Triple Kills" : List[int],
#     "Result" : List[int],
#     "Assists" : List[int],
#     "Penta Kills" : List[int],
#     "Headshots %" : List[int],
#     "K/D Ratio" : List[Union[float, int]],
#     "Quadro Kills" : List[int],
#     "Kills" : List[int],
#     "elo" : float,
#     "elo_history" : List[float]
#     }

# match_json takes the form
# match_id : {
#     "game_mode" : str,
#     "map" : str,
#     "number_of_rounds" : int,
#     "team_one_score" : str,
#     "team_two_score" : str,
#     "players" : List[str],
#     "team_one" : List[str],
#     "team_two" : List[str],
#     "winner" : int,
#     "player_stats" : Dict[str, Dict[str, Union[float, int]]],
#     "player_elo_data" : Dict[str, Dict[str, float]],
#     "match_elo" : float,
#     "team_one_elo" : float,
#     "team_two_elo" : float
# }

api_key = os.environ["API_KEY"]

TypeJSON = Union[Dict[str, 'JSON'], List['JSON'], int, str, float, bool, None]

async def get_match(session, url):
    "Makes a single get request to retrieve match stats"
    async with session.get(url, headers = {"Authorization" : "Bearer " + api_key}) as resp:
        match = await resp.json(loads = ujson.loads)
        try:
            return match["rounds"][0]
        except:
            return None

async def match_loop(match_list : List[str]) -> TypeJSON:
    "Loops through match_list and makes asynchronus get requests to retrieve match data"

    async with aiohttp.ClientSession(json_serialize = ujson.dumps) as session:

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

    def __init__(self, hub_id : str, player_json : TypeJSON = None, match_json : TypeJSON = None):
        self.hub_id = hub_id
        self.player_json = player_json
        self.match_json = match_json
        if player_json is None:
            self.player_json = {}
        if match_json is None:
            self.match_json = {}

    def _limited_match_list(self, offset : int, limit : int) -> List[str]:
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

    def get_full_match_list(self, offset : int, limit : int) -> List[str]:
        """
        Returns a list containing all Match IDs from a specified Faceit Hub.

        Paramters
        ---------

        offset : int
                The number of the earliest match to fetch
        actual_limit : int
                The number of matches to fetch in total.

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

    def parse_match(self, match_id : str, match_data) -> None:

        """
        Parses player and match data for a single match, updates self.match_json and self.player_json
        """
        Player.parse_match_data(match_id, match_data, self.player_json)
        Match.full_parse(match_id, match_data, self.match_json, self.player_json)

    def full_match_loop(self, offset : int, limit : int) -> List[str]:
        """
        Parses player and match data for all matches, updates self.match_json and self.player_json
        """
        job = get_current_job()
        job.meta["progress"] = job.meta.get("progress", 0)
        job.save_meta()
     
        match_id_list = self.get_full_match_list(offset, limit)
        match_data = asyncio.run(match_loop(match_id_list))

        job.meta["length"] = len(match_id_list)
        job.save_meta()
        
        for match_id, data in zip(match_id_list[::-1], match_data[::-1]): # Which way?
            logging.debug(match_id)
            self.parse_match(match_id, data)
            job.meta["progress"] += 1
            job.save_meta()

        return match_id_list
        
    def partial_match_loop(self, offset : int, limit : int, old_match_id_list : List[str]) -> List[str]:
        
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
        new_match_id_list.reverse() # Reversing to maintain order
        new_match_data = asyncio.run(match_loop(new_match_id_list))
        
        for match_id, data in zip(new_match_id_list, new_match_data):
            logging.debug(match_id)
            self.parse_match(match_id, data)

        return match_id_list

class Match:

    def __init__(self, match_id : str):

        self.match_id = match_id
        self.json = {}
        self.player_stats = {}
        self.player_elo_data = {}

    def match_parse(self, data : TypeJSON) -> None:

        "Populates json attribute with statistics from the match"
        
        self.json["game_mode"] = data["game_mode"]
        self.json["number_of_rounds"] = int(data["round_stats"]["Rounds"])
        self.json["map"] = data["round_stats"]["Map"].split("/")[-1]
        self.json["team_one_score"] = data["teams"][0]["team_stats"]["Final Score"]
        self.json["team_two_score"] = data["teams"][1]["team_stats"]["Final Score"]
        self.json["team_one"] = [player["player_id"] for player in data["teams"][0]["players"]]
        self.json["team_two"] = [player["player_id"] for player in data["teams"][1]["players"]]
        self.json["players"] = self.json["team_one"] + self.json["team_two"]

        self.json["winner"] = 1 + (int(self.json["team_two_score"]) > int(self.json["team_one_score"]))

        self.player_stat_parse(data, 1)
        self.player_stat_parse(data, 2)

    def to_json(self) -> TypeJSON:
        "Returns json object ready to be inserted into match_json"
        self.json["player_stats"] = self.player_stats
        self.json["player_elo_data"] = self.player_elo_data
        self.json["match_elo"] = self.match_elo
        self.json["team_one_elo"] = self.team_one_elo
        self.json["team_two_elo"] = self.team_two_elo
        return {self.match_id : self.json}

    def player_stat_parse(self, data : TypeJSON, team : List[str]) -> None:
        "Populates player_stats attribute with player stats from the match"

        num_team_players = len([self.json["team_one"], self.json["team_two"]][team - 1]) # Teams may not always show as 5 due to abandons

        for i in range(num_team_players):

            player = data["teams"][team - 1]["players"][i]["player_id"]
            player_stats = data["teams"][team - 1]["players"][i]["player_stats"]

            self.player_stats[player] = player_stats

            for stat in self.player_stats[player].keys():
                self.player_stats[player][stat] = float(self.player_stats[player][stat])
            self.player_stats[player]["Number of Rounds"] = self.json["number_of_rounds"]
    
    @staticmethod
    def scoreboard_data(data : TypeJSON) -> TypeJSON:
        "Returns player stats for each team in JSON format"
        team_one_data = {player : data["player_stats"][player] for player in data["team_one"]}
        team_two_data = {player : data["player_stats"][player] for player in data["team_two"]}

        return team_one_data, team_two_data

    @staticmethod
    def full_parse(match_id : str, match_data : TypeJSON, match_json : TypeJSON, player_json : TypeJSON) -> None:
        "Parses all stats related to a single match and updates both match_json and player_json"
        if match_data is None:
            return None
        current_match = Match(match_id)
        current_match.match_parse(match_data)
        current_match_elo = Elo(current_match.json["team_one"], current_match.json["team_two"], current_match.player_stats, player_json)
        current_match.match_elo = current_match_elo._match_elo
        current_match.team_one_elo = current_match_elo.team_one_elo
        current_match.team_two_elo = current_match_elo.team_two_elo
        winning_team = [current_match.json["team_one"], current_match.json["team_two"]][current_match.json["winner"] - 1]
        total_elo_change = 0
        for player in current_match.json["players"]:
            elo_change, target_performance, actual_performance = current_match_elo.elo_changes(player, (player in winning_team))
            current_match.player_elo_data[player] = {
                "Elo" : player_json[player]["elo"],
                "Elo Change" : elo_change,
                "Performance Target" : target_performance,
                "Performance Actual" : actual_performance
                }
            total_elo_change += elo_change
            player_json[player]["elo"] += elo_change
            player_json[player]["elo_history"].append(player_json[player]["elo"])
        current_match.json_update(match_json)

    def json_update(self, data : TypeJSON):
        "Adds match stats as entry into data under match_id"
        data.update(self.to_json())

class Player:
    
    def __init__(self, player_id : str):
        
        self.name = None
        self.player_id = player_id
        self.stats = {
            "Match ID" : [],
            "Number of Rounds" : [],
            "Map" : [],
            'Deaths': [],
            'K/R Ratio': [],
            'MVPs': [],
            'Headshots': [],
            'Triple Kills': [],
            'Result': [],
            'Assists': [],
            'Penta Kills': [],
            'Headshots %': [],
            'K/D Ratio': [],
            'Quadro Kills': [],
            'Kills': []
            }
        self.elo = 1000
        self.elo_history = []

    def to_json(self) -> TypeJSON:
        "Returns json to match format of player_json"

        return {
            f"{self.player_id}" : {
                "name" : self.name,
                "stats" : self.stats,
                "elo" : self.elo,
                "elo_history" : self.elo_history
            }
        }

    @staticmethod
    def stat_parse(data : TypeJSON, match_id : str, total_rounds, match_map : str, statistics) -> None:
            
        data["stats"]["Match ID"].append(match_id)
        data["stats"]["Number of Rounds"].append(int(total_rounds))
        data["stats"]["Map"].append(match_map)

        for statistic in statistics:
            data["stats"][statistic].append(float(statistics[statistic]))

    @staticmethod
    def json_init() -> TypeJSON:
        "Returns an unpopulated Json object for players who are not in the player_json yet"
        return {
            "name" : None,
            "stats" : {
                "Match ID" : [],
                "Number of Rounds" : [],
                "Map" : [],
                'Deaths': [],
                'K/R Ratio': [],
                'MVPs': [],
                'Headshots': [],
                'Triple Kills': [],
                'Result': [],
                'Assists': [],
                'Penta Kills': [],
                'Headshots %': [],
                'K/D Ratio': [],
                'Quadro Kills': [],
                'Kills': []
            },
            "elo" : 1000,
            "elo_history" : []
        }

    @classmethod
    def parse_match_data(cls, match_id : str, match_data : TypeJSON, player_dict : TypeJSON) -> None:
        """
        Retrieves player stats from match data and adds them to player_dict.

        Parameters
        ----------

        match_id : str
                text
        match_data : dict, JSON
                text
        player_dict : dict
                text
        insert : bool False
                text

        Returns
        -------

        None

        """
        
        if match_data == None:
            
            return None
        
        total_rounds = match_data["round_stats"]["Rounds"]
        match_map = match_data["round_stats"]["Map"]
        
        for team in match_data["teams"]:
            for player in team["players"]:
                if player["player_id"] not in player_dict.keys():
                    player_dict[player["player_id"]] = cls.json_init()
                player_dict[player["player_id"]]["name"] = player["nickname"]
                cls.stat_parse(player_dict[player["player_id"]], match_id, total_rounds, match_map, player["player_stats"])

        return None

    def json_update(self, data : TypeJSON) -> None:
        "Updates the data object with the stats from the latest match"

        if self.player_id not in data:
            data.update(self.to_json())
            return None

        data[self.player_id]["name"] = self.name
        data[self.player_id]["elo"] = self.elo
        data[self.player_id]["elo_history"].append(self.elo)
        for key, val in self.stats.items():
            data[self.player_id]["stats"][key].append(val[-1])

if __name__ == "__main__":
    pass