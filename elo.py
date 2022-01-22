class Elo:

    def __init__(self, team_one, team_two, player_dict):
        self.player_dict = player_dict
        self.team_one = team_one
        self.team_two = team_two
        self.team_one_elo = sum([player_dict[player].elo for player in self.team_one]) / len(self.team_one)
        self.team_two_elo = sum([player_dict[player].elo for player in self.team_two]) / len(self.team_two)
        self._match_elo = self._match_elo()
        self.team_one_elo_win = self._team_elo_win(self.team_one)
        self.team_two_elo_win = self._team_elo_win(self.team_two)

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
        max_allowed_difference = 400
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

        return team_elo_reward

    def performance_metric(self, player, stats):
        """
        Calculates the performance rating of an individual based on the stats provided.

        Parameters
        ----------

        player : str

        stats : dict

        Returns
        -------

        performance_rating : float
        """

        performance_rating = stats["K/R Ratio"]


        return performance_rating

    def performance_target(self, player):

        max_elo_diff = 400 # If you are 400 elo above match elo, target increased by 50%, 400 below target reduced by 50%

        performance_average = 1

        player_elo_diff = self.player_dict[player].elo - self._match_elo

        target_multiplier = max(min(player_elo_diff - max_elo_diff, max_elo_diff), -max_elo_diff)
        target_multiplier = 1 + (target_multiplier / (max_elo_diff * 2))

        return performance_average * target_multiplier

    def elo_changes(self, player, stats, win):

        target = self.performance_target(player)
        actual = self.performance_metric(player, stats)
        performance_ratio = min(1.5, max(0.5, ((actual / target)))) # Between 0.5 and 1.5
        
        if win:
            return performance_ratio * [self.team_one_elo_win, self.team_two_elo_win][1 - (player in self.team_one)]
        return - (abs(performance_ratio - 2)) * [self.team_two_elo_win, self.team_one_elo_win][1 - (player in self.team_one)]

    @classmethod
    def even_match(self, players):

        pass
