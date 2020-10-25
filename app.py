import os
from flask import Flask, flash, render_template, redirect, url_for, request, json

from flask_migrate import Migrate
from flask_seeder import FlaskSeeder
from datetime import datetime
import tzlocal
import requests
import flask_login
from models import db, Channel, User
from hashids import Hashids

seeder = FlaskSeeder()
hashids = Hashids()

basedir = os.path.abspath(os.path.dirname(__file__))
testDB = os.path.join(basedir, 'test.db')
app = Flask(__name__)
app.secret_key = 'ekDiAhArrhpwMRid3F6YEVaMk0d9U02Y'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'sqlite:///' + testDB
db.init_app(app)
migrate = Migrate(app, db)
seeder.init_app(app, db)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)


class Auth(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    user = User.query.filter_by(email=email).first()

    if not isinstance(user, User):
        return

    auth = Auth()
    auth.id = user.email
    auth.user = user
    return auth


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html", url=request.url_root)

    email = request.form.get("email", None)
    remember = True if not request.form.get("remember", None) else False

    user = User.query.filter_by(email=email, password=request.form['password']).first()

    if isinstance(user, User):
        auth = Auth()
        auth.id = user.email
        auth.user = user

        flask_login.login_user(auth, remember=remember)
        return redirect(url_for('index'))

    flash('Email or password incorrect. Please try again.', category='danger')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('login'))


@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for("login"))


@app.route("/")
@flask_login.login_required
def index():
    if flask_login.current_user.user.role == "admin":
        channels = Channel.query.all()
    else:
        channels = Channel.query.filter_by(user_id=flask_login.current_user.user.id).all()
    return render_template("project/index.html", channels=channels, url=request.url_root)


@app.route("/detail/<string:id>")
@flask_login.login_required
def detail(id):
    if flask_login.current_user.user.role == "admin":
        channel = Channel.query.filter_by(id=id).first()
    else:
        channel = Channel.query.filter_by(id=id, user_id=flask_login.current_user.user.id).first()

    if isinstance(channel, Channel):
        return render_template("project/detail.html", channel=channel, url=request.url_root)
    else:
        flash("Project not found", "danger")
        return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
@flask_login.login_required
def add_channel():
    name = request.form.get("name")

    new_channel = Channel(name=name, slack_webhook="", user_id=flask_login.current_user.user.id, discord_webhook="",
                          count=0, active=True)
    db.session.add(new_channel)
    db.session.commit()
    new_channel.code = hashids.encode(new_channel.id + 100)
    db.session.commit()
    flash("Project added successfully", "success")
    return redirect(url_for("detail", id=new_channel.id))


@app.route("/webhook/<string:id>", methods=["POST"])
def webhook(id):
    project_name = request.json.get("project_name")
    message = request.json.get("message")
    event = request.json.get("event")
    url = request.json.get("url")
    channel = Channel.query.filter_by(code=id).first()
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
@flask_login.login_required
def active_channel(id):
    channel = Channel.query.filter_by(id=id).first()
    channel.active = not channel.active
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/edit/<string:id>", methods=["POST"])
@flask_login.login_required
def edit(id):
    if flask_login.current_user.user.role == "admin":
        channel = Channel.query.filter_by(id=id).first()
    else:
        channel = Channel.query.filter_by(id=id, user_id=flask_login.current_user.user.id).first()

    if not isinstance(channel, Channel):
        flash("Project not found", "danger")
        return redirect(url_for("index"))

    name = request.form.get("name")
    discord_webhook = request.form.get("discord_webhook")
    slack_webhook = request.form.get("slack_webhook")
    channel.name = name
    channel.discord_webhook = discord_webhook
    channel.slack_webhook = slack_webhook
    db.session.commit()
    flash("Project update successfully", "success")
    return redirect(url_for("detail", id=channel.id))


@app.route("/delete/<string:id>")
@flask_login.login_required
def delete_channel(id):
    if flask_login.current_user.user.role == "admin":
        channel = Channel.query.filter_by(id=id).first()
    else:
        channel = Channel.query.filter_by(id=id, user_id=flask_login.current_user.user.id).first()

    if not isinstance(channel, Channel):
        flash("Project not found", "danger")
        return redirect(url_for("index"))

    db.session.delete(channel)
    db.session.commit()
    flash("Project deleted successfully", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, host="0.0.0.0", port=8080)
