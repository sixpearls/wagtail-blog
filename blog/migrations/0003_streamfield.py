# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from wagtail.wagtailcore.rich_text import RichText


def convert_to_streamfield(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    for post in BlogPost.objects.all():
        if post.content.raw_text and not post.content:
            post.content = [('paragraph', RichText(post.content.raw_text))]
            post.save()


def convert_to_richtext(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPost")
    for post in BlogPost.objects.all():
        if post.content.raw_text is None:
            raw_text = ''.join([
                child.value.source for child in post.content
                if child.block_type == 'paragraph'
            ])
            post.content = raw_text
            post.save()

class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_update_foreignkey'),
    ]

    operations = [
        migrations.RunPython(
            convert_to_streamfield,
            convert_to_richtext,
        ),
    ]
