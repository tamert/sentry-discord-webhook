import os
from flask import Flask, render_template, redirect, url_for, request, json
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
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
    webhook = db.Column(db.String(300))
    count = db.Column(db.Integer)
    active = db.Column(db.Boolean)


@app.route("/")
def index():
    channels = Channel.query.all()
    return render_template("index.html", channels=channels, url=request.url_root)


@app.route("/add", methods=["POST"])
def add_channel():
    name = request.form.get("name")
    webhook = request.form.get("webhook")
    new_channel = Channel(name=name, webhook=webhook, count=0, active=True)
    db.session.add(new_channel)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/webhook", methods=["POST"])
def webhook():
    project_name = request.json.get("project_name")
    message = request.json.get("message")
    culprit = request.json.get("culprit")
    url = request.json.get("url")

    channel = Channel.query.filter_by(name=project_name).first()
    if channel:
        channel.count = 1 if channel.count is None else (channel.count + 1)
        db.session.comit()

        res = requests.post(channel.webhook,
                            json={"username": "sentry",
                                  "embeds": [
                                      {
                                          "title": message,
                                          "description": culprit,
                                          "color": 15746887
                                      }
                                  ],
                                  "content": "Visit issue: <%s>" % url
                                  }
                            )
        if res.ok:
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
                    "message": "Request webhook failed"
                }),
                status=400,
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


@app.route("/delete/<string:id>")
def delete_channel(id):
    channel = Channel.query.filter_by(id=id).first()
    db.session.delete(channel)
    db.session.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True, port=8080)
