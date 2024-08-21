from aiogram.utils.formatting import PhoneNumber
from peewee import *
from dotenv import dotenv_values
import datetime
import uuid

config = dotenv_values(".env")

# Database configuration
db = PostgresqlDatabase(
    config.get("db_name"),
    user=config.get("user"),
    password=config.get("passw"),
    host=config.get("host"),
    port=config.get("port")
)


class BaseModel(Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, null=True)
    create_datetime = DateTimeField(default=datetime.datetime.now, null=True)

    class Meta:
        database = db


# UsersTable
class UsersTable(BaseModel):
    tg_id = CharField()
    full_name = CharField(null=True)  # User's full name
    birthday = DateTimeField(null=True)
    phone = CharField(null=True)

