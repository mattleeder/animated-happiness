from dash import dash, dcc, html
import dash_bootstrap_components as dbc
from player import Player

stat_page = html.Div([
    html.Div([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Dropdown(id = "player-name-dropdown", multi = True),
                            html.Br(),
                            dcc.Dropdown(
                                id = "stat-name-dropdown", 
                                options = [{"label" : x, "value" : x} for x in sorted(Player("").stats.keys())],
                                multi = False,
                                value = "Kills"
                            )
                        ])
                    ])
                ], width = 2),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Graph(id = 'scatter'),
                            dcc.Slider(
                                id = "n-recent-matches",
                                min=1,
                                max = 20,
                                step = 1,
                                marks={i : f"{i}" for i in range(1, 21)},
                                value=10
                            )
                        ])
                    ])
                ], width = 10)
            ], align = "center")
        ])
    ], style = {"background-color" : "dark"}),
    html.Br(),
    html.Div([
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Div(id = "stat-table", children = [
                            dash.dash_table.DataTable(id='ordered_stat_table')
                        ])
                    ], width = 6),
                    dbc.Col([
                        html.Div(id = "elo-div", children = [
                            dash.dash_table.DataTable(id='ordered_stat_table')
                        ])
                    ], width = 6)
                ], align = "center")
            ])
        ], style = {"background-color" : "dark"})
    ])
])

match_page = html.Div([
    dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.Div(id = "match-explorer-main", children = [
                    html.Div(id = 'match-explorer-h3'),
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dcc.Dropdown(id = "player-filter", multi = False, value = "All")
                            ]),
                            dbc.Row([
                                dcc.Dropdown(
                                    id = 'match-choices'
                                )
                            ])
                        ]),
                    ], style = {"background-color" : "dark"}),
                    html.Br([]),
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id = "scoreboard-container")
                        ])
                    ], style = {"background-color" : "dark"})
                ])
            ])
        ])
    ])
])

elo_page = html.Div([
    html.Br(),
    html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H3("Elo")
                    ])
                ]),
                html.Br(),
                dbc.Card([
                    dbc.CardBody([
                html.Div(id = "full-elo-table")
                    ])
                ], style = {"background-color" : "dark"})
            ])
        ])
    ])
])

match_balance_page = html.Div([
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div(id = 'match-create-main', children = [
                        html.Div([
                            dcc.Dropdown(id = 'elo-filter', multi = True),
                        ]),
                        html.Div(id = 'match-create')
                    ])
                ])
            ])
        ])
    ])
])

elo_high_score_page = html.Div([
    html.Br(),
    html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H3("Elo Hi-Scores")
                    ])
                ]),
                html.Br(),
                dbc.Card([
                    dbc.CardBody([
                        html.Div(id = "elo-hiscores-table")
                        ])
                ], style = {"background-color" : "dark"})
            ])
        ])
    ])
])


data_retrieve_page = html.Div([
    html.Div([
        dcc.Input(id="hub-id", type="text", placeholder="", debounce=True),
    ]),
    html.Div([
        html.Button("Download Dashboard Data", id="download-button"),
        dcc.Download(id="download-output")
    ]),
    html.Div([
        html.Button("Fetch Dashboard Data", id="fetch-button"),
    ]),
    html.Div([
        html.Button("Update Dashboard Data", id="update-button"),
    ]),
    html.Div([
        dcc.Upload(id = "data-upload", children = [
            html.Button("Data Upload", id = "data-upload-button")
        ]),
    ]),
    html.Div(id = "data-retrieve-msg")
])
