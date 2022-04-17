window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        get_chosen_match_data: function(chosen_match, match_json) {
            return Array(
                chosen_match,
                match_json[chosen_match]
            );
        }
    }
});