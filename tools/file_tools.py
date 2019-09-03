import os

def remove_oldest_file(dir):

    list_of_files = os.listdir(dir)
    full_path = [os.path.join(dir, "{0}".format(x)) for x in list_of_files]

    if len([name for name in list_of_files]) == 25:
        oldest_file = min(full_path, key=os.path.getctime)
        os.remove(oldest_file)