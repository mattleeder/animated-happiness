import pandas as pd
from sklearn import linear_model
import numpy as np


class Player:

    # self.player_dict = player_dict
    
    def __init__(self, player_id):
        
        self.name = None
        self.player_id = player_id
        self.stats = {"Match ID" : [],
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
                      'Kills': []}
        self.elo = 1000
        self.elo_history = []

    def to_json(self):

        return {
            f"{self.player_id}" : {
                "name" : self.name,
                "stats" : self.stats,
                "elo" : self.elo,
                "elo_history" : self.elo_history
            }
        }

    @staticmethod
    def stat_parse(data, match_id, total_rounds, match_map, statistics):
            
        data["stats"]["Match ID"].append(match_id)
        data["stats"]["Number of Rounds"].append(int(total_rounds))
        data["stats"]["Map"].append(match_map)

        for statistic in statistics:
            data["stats"][statistic].append(float(statistics[statistic]))
    
    @staticmethod
    def avg_last_n_matches(data, n, stat, per_round = False):
        
        total = sum(data["stats"][stat][0:n])
        
        if per_round:
            total_rounds = sum(data["stats"]["Number of Rounds"][0:n])
            total /= total_rounds
            
            return total

        total /= n
        return total

    @staticmethod
    def stats_last_n_matches(data, n, stat, per_round = False):

        stats = data["stats"][stat][0:n]

        if per_round:
            rounds = data["stats"]["Number of Rounds"][0:n]
            return [s / r for s, r in zip(stats, rounds)]
        
        return stats
    
    @staticmethod
    def stat_ratio_last_n_matches(data, n, numerator_stat, denominator_stat):
        numerator = sum(data["stats"][numerator_stat][0:n])
        denominator = sum(data["stats"][denominator_stat][0:n])
        
        return numerator / denominator

    def linear_regression(self, stat, n, per_round = False):

        lm = linear_model.LinearRegression()
        data = self.stats_last_n_matches(n, stat, per_round)
        lm.fit(np.array(range(1, n+1)).reshape(-1, 1), data)

        return lm.predict(np.array([n+1]).reshape(1, -1))
    
    @property
    def stats_df(self):
        
        d = {key : value for key, value in self.stats.items()}
        df = pd.DataFrame(d)

        return df
    
    @classmethod
    def order_players_by_stat(cls, player_dict, list_of_players, n, numerator_stat, denominator_stat = None):
        
        order_dict = {}
        
        if denominator_stat == None:
            for player in list_of_players:
                avg_stat = cls.avg_last_n_matches(player_dict[player], n, numerator_stat)
                order_dict[avg_stat] = player
        else:
            for player in list_of_players:
                avg_stat = cls.stat_ratio_last_n_matches(player_dict[player], n, numerator_stat, denominator_stat)
                order_dict[avg_stat] = player

        return order_dict

    @staticmethod
    def json_init():
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
    def parse_match_data(cls, match_id, match_data, player_dict):
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

    def json_update(self, data):

        if self.player_id not in data:
            data.update(self.to_json())
            return None

        data[self.player_id]["name"] = self.name
        data[self.player_id]["elo"] = self.elo
        data[self.player_id]["elo_history"].append(self.elo)
        for key, val in self.stats.items():
            data[self.player_id]["stats"][key].append(val[-1])