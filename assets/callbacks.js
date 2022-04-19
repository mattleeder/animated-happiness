window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        get_chosen_match_data: function(chosen_match, match_json) {
            return Array(
                chosen_match,
                match_json[chosen_match]
            );
        },
        get_match_choices: function(player_filter, match_json, match_list) {
            if (player_filter === "All") {
                return Array(
                    match_list.map(x => ({"label" : x, "value" : x})),
                    match_list.map(x => ({"label" : x, "value" : x}))[0]["value"]
                );
            }
            var ops = [];
            for (const match_id of match_list) {
                var match = match_json[match_id];
                if (typeof match !== "undefined") {
                    if (match_json[match_id]["players"].includes(player_filter)) {
                        ops.push({"label" : match_id, "value" : match_id});
                    }
                }
            }
            return Array(
                ops,    
                ops[0]["value"]
            )
        },
        get_player_stat_data: function(player_name_dropdown, stat_name_dropdown, n, player_json) {
            var data = {};
            data["Match Number"] = [];
            data["Player"] = [];
            data["Elo"] = [];
            data[stat_name_dropdown] = [];

            for (const player of player_name_dropdown) {
                var n_matches = Math.min(n, player_json[player]["stats"]["Match ID"].length);
                var name = player_json[player]["name"];
                data["Player"].push(...Array(n_matches).fill(name));
                data["Match Number"].push(...Array(n_matches).fill().map((_, i) => i + n - n_matches));
                data["Elo"].push(...Array(n_matches).fill(Math.round(player_json[player]["elo"])));
                stat_list = player_json[player]["stats"][stat_name_dropdown].slice(-n);
                data[stat_name_dropdown].push(...stat_list);
            }
            return data;
        },
        get_elo_data: function(player_json) {
            var data = {};
            data["Player"] = [];
            data["Current Elo"] = [];
            data["Max Elo"] = [];
            for (const player of Object.keys(player_json)) {
                data["Player"].push(player_json[player]["name"]);
                data["Current Elo"].push(player_json[player]["elo"]);
                data["Max Elo"].push(Math.max(...player_json[player]["elo_history"]));
            }
            return data;
        },
        player_dropdown_options_stat_page: function(player_name_lookup) {
            player_name_lookup = player_name_lookup.map(({ key}) => (key));
            player_name_lookup.sort();
            return player_name_lookup.map(x => ({"label" : x, "value" : x}));
        }
    }
});