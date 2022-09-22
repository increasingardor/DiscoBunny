import asyncio
import sqlite3
import aiosqlite
import datetime
import pytz

class Setting:
    def __init__(self, setting, db):
        self.__dict__["db"] = db
        for key in setting.keys():
            self.__dict__[key] = setting[key]

    async def __setattr__(self, attr_name, attr_value):
        if attr_name == "setting_id":
            raise AttributeError("setting_id cannot be set manually")
        if attr_name not in self.__dict__:
            raise AttributeError("Arbitrary attributes may not be added")
        async with self.db:
            await self.db.execute(f"update settings set {attr_name} = ? where setting_id = ?", (attr_value, self.setting_id))
            await self.db.commit()
        self.__dict__[attr_name] = attr_value

    async def delete(self):
        async with self.db:
            await self.db.execute("delete from settings where setting_id = ?", (self.setting_id,))
            await self.db.commit()


class Settings:
    def __init__(self, connection):
        self.db = connection
        self.db.row_factory = sqlite3.Row
#        self.db = await asqlite.connect(connection)
#        self.db.row_factory = sqlite3.Row
#        asyncio.run(self._start(connection))

    async def _start(self, connection):
        self.db = await aiosqlite.connect(connection)
        self.db.row_factory = sqlite3.Row

    async def get(self, attr, *, all=False):
        setting = await self.db.execute("select setting_id, name, value, description, created_by, created_date from settings where name = ?", (attr,))
        result = await setting.fetchone()
        if result:
            if all:
                return result
            else:
                return result["value"]
        else:
            raise AttributeError

    async def set(self, attr, value):
        if attr == "setting_id":
            raise AttributeError("setting_id cannot be set manually")
        keys = await self.keys()
        if attr not in keys:
            raise AttributeError("That settings does not exist, please add it.")
        await self.db.execute(f"update settings set value = ? where name = ?", (value, attr))
        await self.db.commit()
        

    async def keys(self):
        result = await self.db.execute("select name from settings")
        settings = await result.fetchall()
        return [setting["name"] for setting in settings]

    async def add(self, name, value, created_by, created_date, description=None):
#        async with self.db:
        await self.db.execute("insert into settings (name, value, description, created_by, created_date) values (?, ?, ?, ?, ?)", (name, value, description, created_by, datetime.datetime.now(pytz.timezone('US/Central'))))
        await self.db.commit()

