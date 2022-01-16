import pandas as pd
from sklearn import linear_model
import numpy as np


class Player:
    
    def __init__(self, name):
        
        self.name = name
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

    def stat_parse(self, match_id, total_rounds, match_map, statistics, insert = False):
        
        if insert == False:
            
            self.stats["Match ID"].append(match_id)
            self.stats["Number of Rounds"].append(int(total_rounds))
            self.stats["Map"].append(match_map)

            for statistic in statistics:
                self.stats[statistic].append(float(statistics[statistic]))
        
        elif insert == True:
            
            self.stats["Match ID"].insert(0, match_id)
            self.stats["Number of Rounds"].insert(0, int(total_rounds))
            self.stats["Map"].insert(0, match_map)

            for statistic in statistics:
                self.stats[statistic].insert(0, float(statistics[statistic]))
            
    def avg_last_n_matches(self, n, stat, per_round = 0):
        
        total = sum(self.stats[stat][0:n])
        
        if per_round == 1:
            total_rounds = sum(self.stats["Number of Rounds"][0:n])
            total /= total_rounds
            
            return total
        else:
            total /= n
            
            return total

    def stats_last_n_matches(self, n, stat, per_round = False):

        stats = self.stats[stat][0:n]

        if per_round:
            rounds = self.stats["Number of Rounds"][0:n]
            return [s / r for s,r in zip(stats, rounds)]
        
        return stats
        
    def stat_ratio_last_n_matches(self, n, numerator_stat, denominator_stat):
        numerator = sum(self.stats[numerator_stat][0:n])
        denominator = sum(self.stats[denominator_stat][0:n])
        
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

    @property
    def winrate(self):
        pass
    
    @classmethod
    def order_players_by_stat(self, player_dict, list_of_players, n, numerator_stat, denominator_stat = None):
        
        order_dict = {}
        
        if denominator_stat == None:
            for player in list_of_players:
                avg_stat = player_dict[player].avg_last_n_matches(n, numerator_stat)
                order_dict[avg_stat] = player
        else:
            for player in list_of_players:
                avg_stat = player_dict[player].stat_ratio_last_n_matches(n, numerator_stat, denominator_stat)
                order_dict[avg_stat] = player

        return order_dict

    @classmethod
    def players_df(self):
        pass