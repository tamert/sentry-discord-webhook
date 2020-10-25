from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    def __init__(self, id=None, name=None, email=None, password=None, role=None):
        self.id = id
        self.name = name
        self.email = email
        self.password = password
        self.role = role

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    email = db.Column(db.String(128))
    password = db.Column(db.String(128))
    role = db.Column(db.String(128))

    channels = db.relationship("Channel", back_populates="user")

    def __str__(self):
        return "ID=%d, Name=%s" % (self.id, self.name)


class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    code = db.Column(db.String(80))
    slack_webhook = db.Column(db.String(300))
    discord_webhook = db.Column(db.String(300))
    count = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="channels")

    active = db.Column(db.Boolean)

    def __str__(self):
        return "ID=%d, Name=%s" % (self.id_num, self.name)

# class Issue(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255))
#     url = db.Column(db.String(255))
#     location = db.Column(db.String(800))
#     created_at = db.Column(db.Integer)
#     channel_id = db.Column(db.Integer)
