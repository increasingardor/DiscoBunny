class Settings:
    def __init__(self, settings):
        for setting in settings:
            try:
                value = int(setting["value"])
            except ValueError:
                value = setting["value"]
            self.__setattr__(setting["name"], value)