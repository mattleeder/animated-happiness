import requests
from elo import Elo
import os

api_key = os.environ["API_KEY"]

class Match:

    def __init__(self, match_id):

        self.match_id = match_id
        self.game_mode = None
        self.map = None
        self.number_of_rounds = None
        self.team_one_score = None
        self.team_two_score = None
        self.players = []
        self.team_one = []
        self.team_two = []
        self.winner = None
        self.player_stats = {}
        self.player_elo_data = {}

        self.match_elo = None
        self.team_one_elo = None
        self.team_two_elo = None

    def match_parse(self, data):
        
        self.game_mode = data["game_mode"]
        self.number_of_rounds = int(data["round_stats"]["Rounds"])
        self.map = data["round_stats"]["Map"].split("/")[-1]
        self.team_one_score = data["teams"][0]["team_stats"]["Final Score"]
        self.team_two_score = data["teams"][1]["team_stats"]["Final Score"]
        self.team_one = [player["player_id"] for player in data["teams"][0]["players"]]
        self.team_two = [player["player_id"] for player in data["teams"][1]["players"]]
        self.players = self.team_one + self.team_two

        self.winner = 1 + (int(self.team_two_score) > int(self.team_one_score))

        self.player_stat_parse(data, 1)
        self.player_stat_parse(data, 2)

    def to_json(self):
        
        return {
            f"{self.match_id}" : {
                "game_mode" : self.game_mode,
                "map" : self.map,
                "number_of_rounds" : self.number_of_rounds,
                "team_one_score" : self.team_one_score,
                "team_two_score" : self.team_two_score,
                "players" : self.players,
                "team_one" : self.team_one,
                "team_two" : self.team_two,
                "winner" : self.winner,
                "player_stats" : self.player_stats,
                "player_elo_data" : self.player_elo_data,
                "match_elo" : self.match_elo,
                "team_one_elo" : self.team_one_elo,
                "team_two_elo" : self.team_two_elo
            }
        }

    def player_stat_parse(self, data, team):

        num_team_players = len([self.team_one, self.team_two][team - 1]) # Teams may not always show as 5 due to abandons

        for i in range(num_team_players):

            player = data["teams"][team - 1]["players"][i]["player_id"]
            player_stats = data["teams"][team - 1]["players"][i]["player_stats"]

            self.player_stats[player] = player_stats

            for stat in self.player_stats[player].keys():
                self.player_stats[player][stat] = float(self.player_stats[player][stat])
            self.player_stats[player]["Number of Rounds"] = self.number_of_rounds
    
    @staticmethod
    def scoreboard_data(data):

        team_one_data = {player : data["player_stats"][player] for player in data["team_one"]}
        team_two_data = {player : data["player_stats"][player] for player in data["team_two"]}

        return team_one_data, team_two_data


    @staticmethod
    def full_parse(match_id, match_data, match_json, player_json):
        if match_data is None:
            return None
        current_match = Match(match_id)
        current_match.match_parse(match_data)
        current_match_elo = Elo(current_match.team_one, current_match.team_two, current_match.player_stats, player_json)
        current_match.match_elo = current_match_elo._match_elo
        current_match.team_one_elo = current_match_elo.team_one_elo
        current_match.team_two_elo = current_match_elo.team_two_elo
        winning_team = [current_match.team_one, current_match.team_two][current_match.winner - 1]
        total_elo_change = 0
        for player in current_match.players:
            elo_change, target_performance, actual_performance = current_match_elo.elo_changes(player, (player in winning_team))
            current_match.player_elo_data[player] = {"Elo" : player_json[player]["elo"],
                                                    "Elo Change" : elo_change,
                                                    "Performance Target" : target_performance,
                                                    "Performance Actual" : actual_performance}
            total_elo_change += elo_change
            player_json[player]["elo"] += elo_change
            player_json[player]["elo_history"].append(player_json[player]["elo"])
        current_match.json_update(match_json)

    def match_stats(self):
        """
        Gets full match stats (game_id, best_of, player stats etc.) for a specific match on faceit.

        Returns
        -------

        match_data : dict JSON
                JSON containing statistics about the match.
        """
        
        url = f"https://open.faceit.com/data/v4/matches/{self.match_id}/stats"
        response = requests.get(url, headers = {"Authorization" : "Bearer " + api_key})
        
        # Why is this here? To catch KeyError when response does not contain "rounds"

        try:

            match_data = response.json()["rounds"][0]
            if response.status_code == 404:
                    return None
            return match_data
        
        except:
            
            return None

    def json_update(self, data):

        data.update(self.to_json())