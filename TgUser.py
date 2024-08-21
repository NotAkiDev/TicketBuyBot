class TgUser:
    def __init__(self, tg_id, phone, full_name, username, is_attached=False):
        self.tg_id = tg_id
        self.phone = phone
        self.full_name = full_name
        self.username = username
        self.is_attached = is_attached
