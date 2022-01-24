from itertools import combinations
import pandas as pd

class Elo:
    
    performance_average = 0.3
    max_elo_difference = 400

    def __init__(self, team_one, team_two, match_stats, player_dict):

        self.player_dict = player_dict
        self.match_stats = match_stats
        self.team_one = team_one
        self.team_two = team_two
        self.team_one_elo = sum([player_dict[player].elo for player in self.team_one]) / len(self.team_one)
        self.team_two_elo = sum([player_dict[player].elo for player in self.team_two]) / len(self.team_two)
        self._match_elo = self._match_elo()
        self.team_one_elo_win = self._team_elo_win(self.team_one)
        self.team_two_elo_win = self._team_elo_win(self.team_two)
        self.team_one_performance_balancer = self.team_performance_target_balance(self.team_one)
        self.team_two_performance_balancer = self.team_performance_target_balance(self.team_two)

    def _match_elo(self):
        """
        Calculates match average elo
        """
        all_players = self.team_one.copy()
        all_players.extend(self.team_two)
        total_elo = 0
        for player in all_players:
            total_elo += self.player_dict[player].elo
        return total_elo / len(all_players)

    def _team_elo_win(self, team):
        # The difference threshold at which max and min elo rewards are
        max_allowed_difference = self.max_elo_difference
        # The max and min elo rewards for the whole team if they win
        max_elo_reward = 245
        min_elo_reward = 5
        standard_elo_reward = (max_elo_reward + min_elo_reward) / 2
        elo_scaling = (standard_elo_reward - min_elo_reward) / max_allowed_difference
        team_elo = 0
        for player in team:
            team_elo += self.player_dict[player].elo
        team_elo /= len(team)
        team_elo_difference = team_elo - self._match_elo
        team_elo_reward = max(min(standard_elo_reward - (team_elo_difference * elo_scaling), max_elo_reward), min_elo_reward)

        return team_elo_reward / len(team)

    def performance_metric(self, player):
        """
        Calculates the performance rating of an individual based on the stats provided.

        Parameters
        ----------

        player : str

        stats : dict
              {'Kills': 10.0, 'MVPs': 1.0, 'Quadro Kills': 0.0, 'Deaths': 5.0, 'K/D Ratio': 2.0, 'Penta Kills': 0.0, 'K/R Ratio': 0.83, 'Result': 0.0, 'Triple Kills': 1.0, 'Assists': 3.0, 'Headshots': 4.0, 'Headshots %': 40.0, 'Number of Rounds': 12}

        Returns
        -------

        performance_rating : float
        """

        kpr = self.match_stats[player]["K/R Ratio"]
        rounds = self.match_stats[player]["Number of Rounds"]
        dpr = self.match_stats[player]["Deaths"] / rounds
        assist_per_round = self.match_stats[player]["Assists"] / rounds

        impact = 2.13 * kpr + 0.42 * assist_per_round -0.41

        performance_rating = 0.3591*kpr -0.5329 * dpr + 0.2372 * impact + 0.1587

        # performance_rating = self.match_stats[player]["K/R Ratio"]


        return performance_rating

    def performance_target(self, player):

        max_elo_diff = self.max_elo_difference # If you are 400 elo above match elo, target increased by 50%, 400 below target reduced by 50%

        player_elo_diff = self.player_dict[player].elo - self._match_elo
        target_multiplier = max(min(1 + (player_elo_diff / (max_elo_diff * 2)), max_elo_diff), -max_elo_diff)      
        return self.performance_average * target_multiplier

    def team_performance_target_balance(self, team):
        team_target_differential = []
        for player in team:
            target_differential = self.performance_metric(player) / self.performance_target(player)
            team_target_differential.append(target_differential)

        team_target_balancer = (sum(team_target_differential) / len(team))

        return team_target_balancer

    def elo_changes(self, player, win):

        balancer = [self.team_one_performance_balancer, self.team_two_performance_balancer][1 - (player in self.team_one)]
        target = self.performance_target(player) * balancer
        actual = self.performance_metric(player)
        performance_ratio = min(1.5, max(0.5, ((actual / target)))) # Between 0.5 and 1.5

        if win:
            return (performance_ratio * [self.team_one_elo_win, self.team_two_elo_win][1 - (player in self.team_one)],
                    target,
                    actual)
        return (- (abs(performance_ratio - 2)) * [self.team_two_elo_win, self.team_one_elo_win][1 - (player in self.team_one)],
                target,
                actual)

    @classmethod
    def even_match(self, players):
        player_names = set([player.name for player in players])
        player_elos = [player.elo for player in players]
        elo_lookup = {player.name : player.elo for player in players}

        target = sum(player_elos) / 2
        team_elo = []
        idx = []
        team_list = []
        team_two_list = []
        
        for i, team in enumerate(list(combinations(player_names, 5))):
            elo = abs(sum([elo_lookup[player] for player in team]) - target)
            team_elo.append(elo)
            idx.append(i)
            team_one = [str(player) for player in team]
            team_list.append(", ".join(team_one))
            team_two = [str(player) for player in player_names.difference(team)]
            team_two_list.append(", ".join(team_two))

        data = pd.DataFrame({"Elo Difference" : team_elo, "Team 1" : team_list, "Team 2" : team_two_list}, index = idx).sort_values(by = "Elo Difference", ascending = True).head(5)

        return data