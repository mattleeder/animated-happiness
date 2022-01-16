import pickle

def pickle_write(filename, stat_dict):
    with open(filename, "wb") as f:
        pickle.dump(stat_dict, f)
    print("Pickle successful!")
        
def pickle_read(filename):
    with open(filename, "rb") as f:
        itemlist = pickle.load(f)
    return itemlist

if __name__ == "__main__":
    pass