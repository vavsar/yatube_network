# Generated by Django 3.1.4 on 2020-12-24 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0012_auto_20201128_0800'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='header',
            field=models.CharField(default='default_title', max_length=160),
            preserve_default=False,
        ),
    ]