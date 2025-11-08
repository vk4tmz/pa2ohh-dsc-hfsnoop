
import os

####################################################################
# Utility / Helper Functions - to be moved/refactored later
####################################################################

def makedirs(dirname:str):
    try:
        os.makedirs(dirname, exist_ok=True)
    except OSError as e:
        print(f"Error creating [{dirname}]. {e}")