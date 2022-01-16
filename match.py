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

        self.match_elo = None
        self.team_one_elo = None
        self.team_two_elo = None

    def match_parse(self, data):
        
        self.game_mode = data["game_mode"]
        self.number_of_rounds = data["round_stats"]
        self.map = data["round_stats"]["Map"].split("/")[-1]
        self.team_one_score = data["teams"][0]["team_stats"]["Final Score"]
        self.team_two_score = data["teams"][1]["team_stats"]["Final Score"]
        self.team_one = [player["nickname"] for player in data["teams"][0]["players"]]
        self.team_two = [player["nickname"] for player in data["teams"][1]["players"]]
        self.players = self.team_one + self.team_two

        self.winner = 1 + (int(self.team_two_score) > int(self.team_one_score))

        self.player_stat_parse(data, 1)
        self.player_stat_parse(data, 2)

    def player_stat_parse(self, data, team):

        num_team_players = len([self.team_one, self.team_two][team - 1]) # Teams may not always show as 5 due to abandons

        for i in range(num_team_players):

            player = data["teams"][team - 1]["players"][i]["nickname"]
            player_stats = data["teams"][team - 1]["players"][i]["player_stats"]

            self.player_stats[player] = player_stats

    def match_elo_calc(self, player_dict):
        
        self.team_one_elo = sum([player_dict[player].elo for player in self.team_one]) / len(self.team_one)
        self.team_two_elo = sum([player_dict[player].elo for player in self.team_two]) / len(self.team_two)
        self.match_elo = (self.team_one_elo + self.team_two_elo) / len(self.players)

    def team_reward_cals(self):

        team_one_elo_diff = self.team_one_elo - self.match_elo
        team_two_elo_diff = self.team_two_elo - self.match_elo

        self.team_one_elo_reward = min(245, max(125 - team_one_elo_diff, 5)) # Max reward 245, min 5
        self.team_two_elo_reward = min(245, max(125 - team_two_elo_diff, 5))

    def player_performance_target(self, player, player_dict):

        # Performance metric = Kills per round

        # Write something that uses a logarithmic calculation to give players a performance target; possibly make use of hub average performance

        max_elo_diff = 400 # If you are 400 elo above match elo, target increased by 50%, 400 below target reduced by 50%

        performance_average = 1

        player_elo_diff = player_dict[player].elo - self.match_elo

        target_multiplier = max(min(player_elo_diff - max_elo_diff, max_elo_diff), -max_elo_diff)
        target_multiplier = 1 + (target_multiplier / (max_elo_diff * 2))

        return performance_average * target_multiplier

    def player_elo_reward_calc(self, player, performance_target, team):
        
        performance_ratio = min(1.5, max((0.5, self.player_stats[player]["Kills"] / self.number_of_rounds) / performance_target)) # Between 0.5 and 1.5

        win = performance_ratio * [self.team_one_elo, self.team_two_elo][team - 1]
        loss = - (abs(performance_ratio - 2)) * [self.team_two_elo, self.team_one_elo][team - 1]

        return (loss, win)

    def scoreboard_data(self):

        team_one_data = {player : self.player_stats[player] for player in self.team_one}
        team_two_data = {player : self.player_stats[player] for player in self.team_two}

        return team_one_data, team_two_data

    @classmethod
    def full_parse(self, match_id, match_data, player_dict, match_dict):
        if match_data is None:
            return None
        current_match = Match(match_id)
        current_match.match_parse(match_data)
        current_match.match_elo_calc(player_dict)
        current_match.team_reward_cals()
        for player in current_match.players:
            current_match.player_performance_target(player, player_dict)
        match_dict[match_id] = current_match


    @classmethod
    def match_list_parse(self, match_list):
        match_dict= {}

        pass





