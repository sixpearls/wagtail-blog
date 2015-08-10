# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import wagtail.wagtailcore.blocks
import wagtail.wagtailembeds.blocks
import django.db.models.deletion
import blog.blocks
import wagtail.wagtailcore.fields
import datetime
import wagtail.wagtailimages.blocks


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_streamfield'),
    ]

    operations = [
        migrations.CreateModel(
            name='AjaxBlogPage',
            fields=[
                ('page_ptr', models.OneToOneField(parent_link=True, primary_key=True, auto_created=True, to='wagtailcore.Page', serialize=False)),
                ('blog_page', models.ForeignKey(related_name='jquery_user', on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, to='blog.BlogType')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
    ]
