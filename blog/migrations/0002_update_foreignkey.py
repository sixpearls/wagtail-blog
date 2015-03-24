# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogpost',
            name='category',
            field=models.ForeignKey(related_name='blog_posts', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='blog.BlogCategory', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='blogpost',
            name='featured_image',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='wagtailimages.Image', null=True),
            preserve_default=True,
        ),
    ]
