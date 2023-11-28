from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class App(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)

class Config(models.Model):
    template_path = models.TextField()

class AppItem(models.Model):
    app = models.ForeignKey(App, on_delete=models.DO_NOTHING)
    config = models.ForeignKey(Config, on_delete=models.CASCADE)

class AppList(models.Model):
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    apps = models.ManyToManyField(AppItem)
