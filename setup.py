from layout import main as appmain

def main():

    app = appmain()
    app.run_server(debug = True)

if __name__ == "__main__":
    main()