from player import Player
import cmdargparse

import pandas as pd

import dash
from dash import html
from dash import dcc
import plotly.graph_objects as go
import plotly.express as px
from dash.dependencies import Input, Output

app = dash.Dash(__name__, title = "CSGO Dashboard", update_title="Loading...")
player_dict, match_list, match_dict = cmdargparse.main()
colours = {
    "background" : "#111111",
    "text" : "#7FDBFF"
}

@app.callback(Output(component_id='scatter', component_property= 'figure'),
        [Input(component_id='player_name_dropdown', component_property= 'value'),
        Input(component_id='stat_name_dropdown', component_property= 'value'),
        Input(component_id="n_recent_matches", component_property="value")])
def graph_update(player_name_dropdown, stat_name_dropdown, n_recent_matches):

    n = n_recent_matches

    data = Player("").stats
    data["Player"] = []
    data["Match Number"] = []

    for player in player_name_dropdown:

        matches = min(n, len(player_dict[player].stats["Match ID"]))
        data["Player"].extend([player] * matches)
        data["Match Number"].extend(list(range(n, n - matches, -1)))

        for stat in Player("").stats.keys():

            data[stat].extend(player_dict[player].stats[stat][:n])

    df = pd.DataFrame(data)

    # fig = go.Figure()

    fig = px.line(df,x = "Match Number", y = stat_name_dropdown, color = "Player")

    # for player in player_name_dropdown:
    #     fig.add_scatter(x = df.loc[df["Player"] == player, "Match Number"], 
    #                     y = df.loc[df["Player"] == player, stat_name_dropdown],
    #                     name = player,
    #                     mode = "lines",
    #                     title = "test")
        

    fig.update_layout(
        plot_bgcolor = colours["background"],
        paper_bgcolor = colours["background"],
        font_color = colours["text"]
    )

    return fig


@app.callback(Output(component_id='div2', component_property= 'children'),
            [Input(component_id='player_name_dropdown', component_property= 'value'),
            Input(component_id='stat_name_dropdown', component_property= 'value'),
            Input(component_id="n_recent_matches", component_property="value")])
def stat_order_grid(player_name_dropdown, stat_name_dropdown, n_recent_matches, denominator_stat = None):
    
    d = Player.order_players_by_stat(player_dict, player_name_dropdown, n_recent_matches, stat_name_dropdown, denominator_stat)
    data = [{stat_name_dropdown : round(key,2), "Player" : d[key]} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(id = "table-output", columns = columns, data = data)


@app.callback(Output(component_id='scoreboard-container', component_property= 'children'),
            [Input(component_id='match_selector', component_property= 'value')])
def display_scoreboard(match_selector):

    current_match = match_dict[match_selector]    
    team_one_data, team_two_data = current_match.scoreboard_data()
    team_one_df = pd.DataFrame(team_one_data).T.reset_index()
    team_two_df = pd.DataFrame(team_two_data).T.reset_index()
    team_one_df.rename(columns = {"index" : "Player"}, inplace = True)
    team_two_df.rename(columns = {"index" : "Player"}, inplace = True)

    return html.Div([html.H3("Team One"),
                   dash.dash_table.DataTable(
                                    id='table',
                                    columns=[{"name": i, "id": i} for i in team_one_df.columns],
                                    data=team_one_df.to_dict('records'),
                                ),
                    html.H3("Team Two"),
                    dash.dash_table.DataTable(
                                    id='table',
                                    columns=[{"name": i, "id": i} for i in team_two_df.columns],
                                    data=team_two_df.to_dict('records'),
                                ),
                    html.H6(f"https://www.faceit.com/en/csgo/room/{match_selector}/scoreboard")
                                ])


    return dash.dash_table.DataTable(id = "table-output", columns = columns, data = data)

    # data = [{stat_name_dropdown : round(key,2), "Player" : d[key]} for key in sorted(d.keys(), reverse = True)]
    # columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

   


@app.callback(Output(component_id='div3', component_property= 'children'),
            [Input(component_id='player_name_dropdown', component_property= 'value'),
            Input(component_id='stat_name_dropdown', component_property= 'value'),
            Input(component_id="n_recent_matches", component_property="value")])
def linear_regression(player_name_dropdown, stat_name_dropdown, n_recent_matches, per_round = False):
    per_round = True
    d = {player : player_dict[player].linear_regression(stat_name_dropdown, n_recent_matches, per_round) for player in player_name_dropdown}
    if per_round:
        stat_name_dropdown += " Per Round"
    stat_name_dropdown = "Linear Regression " + stat_name_dropdown
    data = [{"Player" : key, stat_name_dropdown : d[key]} for key in sorted(d.keys(), reverse = True)]
    columns = [{"name" : stat_name_dropdown, "id" : stat_name_dropdown}, {"name" : "Player", "id" : "Player"}]

    return dash.dash_table.DataTable(id = "table-output", columns = columns, data = data)


@app.callback(Output('tabs-content', 'children'),
              Input('tab-selector', 'value'))
def render_content(tab):
    if tab == 'homepage':
        return html.Div(id = "parent", style = {"backgroundColor" : colours["background"]}, className = "eight columns",
                        children = [html.Div([
                                            html.Div([html.H2()]),
                                            html.Div([
                                                    dcc.Dropdown(id = 'player_name_dropdown', 
                                                                options = [{"label" : x, "value" : x} for x in sorted(player_dict.keys())],
                                                                multi = True,
                                                                value = cmdargparse.default_player
                                                                )],
                                                    style={"backgroundColor" : colours["background"]},
                                                    className = "eight columns"
                                                    ),
                                            html.Div([
                                                    dcc.Dropdown(id = "stat_name_dropdown", 
                                                                options = [{"label" : x, "value" : x} for x in sorted(Player("").stats.keys())],
                                                                multi = False,
                                                                value = "Kills"
                                                                )],
                                                    style={"backgroundColor" : colours["background"]},
                                                    className = "eight columns"
                                                    ),
                                            html.Div([
                                                    dcc.Graph(id = 'scatter')],
                                                    className = "eight columns"
                                                    ),
                                            html.Div([
                                                    dcc.Slider(id = "n_recent_matches",
                                                            min=1,
                                                            max = 20,
                                                            marks={i : f"{i}" for i in range(1, 21)},
                                                            value=10
                                                            )],
                                                    className = "eight columns",
                                                    style = {"backgroundColor" : colours["background"]}
                                                    ),
                                            html.Div(id = "div2", children = [
                                                    dash.dash_table.DataTable(id='ordered_stat_table')
                                                    ],
                                                    className = "eight columns",
                                                    style = {"backgroundColor" : colours["background"]}
                                                    ),
                                            html.Div(id = "div3", children = [
                                                    dash.dash_table.DataTable(id='regression_table')
                                                    ],
                                                    className = "eight columns",
                                                    style = {"backgroundColor" : colours["background"]}
                                                    )
                                    ])
                                ]
                )

    elif tab == 'match_explorer':
        return html.Div(id = "match-explorer-main", children = [
                        html.H3("Match Explorer"),
                        html.Div([dcc.Dropdown(id = "match_selector",
                                            options = [{"label" : x, "value" : x} for x in match_list],
                                            multi = False,
                                            value = match_list[-1])
                                            ]),
                        html.Div(id = "scoreboard-container", children = [
                                # dash.dash_table.DataTable(id = "scoreboard")
                                ])
        ])


def main():
    
    app.css.append_css({'external_url': '/assets/stylesheet.css'})
    # app.server.static_folder = 'static'  # if you run app.py from 'root-dir-name' you don't need to specify

    app.layout = html.Div([
    html.H1(f"CSGO Dashboard - Number of matches: {len(match_list)}", className = "banner"),
    dcc.Tabs(id="tab-selector", value='match_explorer', children=[
        dcc.Tab(label='Homepage', value='homepage'),
        dcc.Tab(label='Match Explorer', value='match_explorer'),
    ]),
    html.Div(id='tabs-content')
])

    return app

if __name__ == "__main__":
    main()