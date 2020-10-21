import os
from flask import Flask, render_template, redirect, url_for, request, json
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import tzlocal
import requests

basedir = os.path.abspath(os.path.dirname(__file__))
testDB = os.path.join(basedir, 'test.db')
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'sqlite:///' + testDB
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    slug = db.Column(db.String(80))
    slack_webhook = db.Column(db.String(300))
    discord_webhook = db.Column(db.String(300))
    count = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    active = db.Column(db.Boolean)


# class Issue(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(255))
#     url = db.Column(db.String(255))
#     location = db.Column(db.String(800))
#     created_at = db.Column(db.Integer)
#     channel_id = db.Column(db.Integer)


@app.route("/")
def index():
    channels = Channel.query.all()
    return render_template("index.html", channels=channels, url=request.url_root)


@app.route("/detail/<string:id>")
def detail(id):
    channel = Channel.query.filter_by(id=id).first()
    return render_template("detail.html", channel=channel, url=request.url_root)


@app.route("/add", methods=["POST"])
def add_channel():
    name = request.form.get("name")
    new_channel = Channel(name=name, slack_webhook="", discord_webhook="", count=0, active=True)
    db.session.add(new_channel)
    db.session.commit()

    return redirect(url_for("detail", id=new_channel.id))


@app.route("/webhook/<string:id>", methods=["POST"])
def webhook(id):
    project_name = request.json.get("project_name")
    message = request.json.get("message")
    event = request.json.get("event")
    url = request.json.get("url")
    channel = Channel.query.filter_by(id=id).first()
    title = project_name + " - " + message if message else "Issue"
    if channel and project_name:
        channel.count = 1 if channel.count is None else (channel.count + 1)
        db.session.commit()

        # new_issue = Issue(title=event["title"],
        #                     location=event["location"],
        #                     created_at=int(event["timestamp"]),
        #                     channel_id=channel)
        #
        # db.session.add(new_issue)
        # db.session.commit()

        unix_timestamp = float(event["timestamp"])
        local_timezone = tzlocal.get_localzone()  # get pytz timezone
        local_time = datetime.fromtimestamp(unix_timestamp, local_timezone)

        if channel.discord_webhook:
            data = {"username": "sentry",
                    "content": ":loudspeaker: Issue Alert",
                    "embeds": [
                        {
                            "title": title,
                            "description": event["title"],
                            "timestamp": str(local_time),
                            "url": url,
                            "color": 14177041
                        }
                    ]
                    }
            r = requests.post(channel.discord_webhook, json=data)
            print(r.text)

        if channel.slack_webhook:
            r = requests.post(channel.slack_webhook,
                              json={
                                  "text": "%s \n%s \nDate: %s \nVisit: %s" % (
                                      title, event["title"], str(local_time), url)}
                              )
            print(r.status_code)

        return app.response_class(
            response=json.dumps({
                "success": True,
                "message": "Channel added a new issue"
            }),
            status=200,
            mimetype='application/json'
        )

    else:
        return app.response_class(
            response=json.dumps({
                "success": False,
                "message": "Channel not found"
            }),
            status=400,
            mimetype='application/json'
        )


@app.route("/active/<string:id>")
def active_channel(id):
    channel = Channel.query.filter_by(id=id).first()
    channel.active = not channel.active
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/edit/<string:id>", methods=["POST"])
def edit(id):
    channel = Channel.query.filter_by(id=id).first()
    name = request.form.get("name")
    discord_webhook = request.form.get("discord_webhook")
    slack_webhook = request.form.get("slack_webhook")
    channel.name = name
    channel.discord_webhook = discord_webhook
    channel.slack_webhook = slack_webhook
    db.session.commit()
    return redirect(url_for("detail", id=channel.id))


@app.route("/delete/<string:id>")
def delete_channel(id):
    channel = Channel.query.filter_by(id=id).first()
    db.session.delete(channel)
    db.session.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True, host="0.0.0.0", port=8080)
