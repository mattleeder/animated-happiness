from soupsieve import match


class Elo:
    
    performance_average = 1
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

        Returns
        -------

        performance_rating : float
        """

        performance_rating = self.match_stats[player]["K/R Ratio"]


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

        print(team)
        print(f"{team_target_balancer = }")

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

        pass
