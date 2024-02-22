import os

class ReadInput:
    def __init__(self,filename='SWFinput.txt',root=os.getcwd()):
        with open(root+filename, 'r') as f:
            for line in f:
                print(line)