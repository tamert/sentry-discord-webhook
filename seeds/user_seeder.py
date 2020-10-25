from flask_seeder import Seeder, Faker, generator
from models import User


class UserSeeder(Seeder):

    # run() will be called by Flask-Seeder
    def run(self):
        # Create a new Faker and tell it how to create User objects
        faker = Faker(
            cls=User,
            init={
                "id": generator.Sequence(),
                "name": generator.Name(),
                "email": "admin@admin.com",
                "password": "secret",
                "role": "admin"
            }
        )

        for user in faker.create(1):
            print("Adding user: %s" % user)
            self.db.session.add(user)
