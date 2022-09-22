import os

def get_cogs():
    cogs = []
    for file in os.listdir("cogs/"):
        if file.endswith(".py"):
            cogs.append(f"cogs.{file.split('.')[0]}")
    return cogs
