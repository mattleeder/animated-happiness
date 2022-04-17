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
        }
    }
});