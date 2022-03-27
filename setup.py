from layout import main as appmain

def main():

    app = appmain()
    server = app.server
    app.run_server(debug = True)

if __name__ == "__main__":
    main()