from dash import dash, dcc, html
import dash_bootstrap_components as dbc
from player import Player

stat_page = html.Div([
    dcc.Store(id = "stat-data"),
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
    dcc.Store(id = 'chosen-match-data'),
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
    html.Br(),
    html.Div([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H2(["Instructions"])
                ]),
                html.P(["If you are fetching data from scratch, copy your hub id into the input box and press the fetch data button. \
                        To upload existing data, click the upload button. If you need to update this data, after it is uploaded \
                        or fetched, copy your hub id into the input box and click the update button. To download the data for late use \
                        simply click the download button."])
            ]),
            html.Br(),
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                            dbc.Input(id="hub-id", type="text", placeholder = "Faceit Hub ID", debounce=True),
                    ]),
                    html.Br(),
                    dbc.Row([
                        dbc.Button("Fetch Dashboard Data", id="fetch-button", className="me-1"),
                    ]),
                    dbc.Row([
                        dbc.Button("Update Dashboard Data", id="update-button", className="me-1"),
                    ]),
                ]),
            ]),
            html.Br(),
            dbc.Card([
                dbc.CardBody([
                    dcc.Upload(id = "data-upload", children = [
                        dbc.Row([
                            dbc.Button("Data Upload", id = "data-upload-button", className="me-1")
                        ])
                    ])
                ])
            ]),
            html.Br(),
            dbc.Card([
                dbc.CardBody([
                    html.Div(id = "data-retrieve-msg"),
                ])
            ]),
            html.Br(),
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Button("Download Dashboard Data", id="download-button", className="me-1"),
                        dcc.Download(id="download-output")
                    ]),
                ])
            ])
        ], width = 4)
    ])
])
