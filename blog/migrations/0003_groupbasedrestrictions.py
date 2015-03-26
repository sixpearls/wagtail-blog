# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0013_update_golive_expire_help_text'),
        ('auth', '0001_initial'),
        ('blog', '0002_update_foreignkey'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageGroupViewRestriction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('completely_hidden', models.BooleanField(default=False, help_text='Check to prevent users not in the permitted group from seeing this at all')),
                ('page', models.ForeignKey(related_name='view_groups', to='wagtailcore.Page')),
                ('permitted_group', models.ForeignKey(related_name='page_view_authorization', to='auth.Group')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
