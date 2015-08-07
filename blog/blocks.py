#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django import forms
from wagtail.wagtailcore.blocks import ChooserBlock, StructBlock, ListBlock, \
    StreamBlock, FieldBlock, CharBlock, RichTextBlock, PageChooserBlock, RawHTMLBlock
from wagtail.wagtailembeds.blocks import EmbedBlock

from django.utils.functional import cached_property

import json
from wagtail.wagtailcore.fields import RichTextArea
from bs4 import BeautifulSoup, Tag, NavigableString

from wagtail.wagtailcore.rich_text import RichText, expand_db_html
from django.utils.safestring import mark_safe

from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailimages.formats import get_image_formats, get_image_format
from wagtail.wagtailimages.models import SourceImageIOError
from django.utils.html import escape
from django.template.loader import render_to_string

class StoryText(RichText):
    def __str__(self):
        return mark_safe(expand_db_html(self.source))

class StoryTextArea(RichTextArea):
    def render_js_init(self, id_, name, value):
        return "makeRichTextEditable({0});".format(json.dumps(id_))

    def value_from_datadict(self, data, files, name):
        # here might be the best place to clean empty paragraphs, unwrapped text, etc.
        # TODO: clean up some html
        # remove: empty ps, replace <br />text with <p>text</p>, make sure lists are outside of paragraphs
        clean_data = super(StoryTextArea, self).value_from_datadict(data, files, name)
        clean_html = BeautifulSoup(clean_data,'html5lib').body
        empty_ps = clean_html.findAll(lambda tag: tag.name == 'p' and tag.find(True) is None and (tag.string is None or tag.string.strip()==""))


        return clean_data

class StoryTextBlock(RichTextBlock):
    @cached_property
    def field(self):
        return forms.CharField(widget=StoryTextArea, **self.field_options)

    def to_python(self, value):
        # convert a source-HTML string from the JSONish representation
        # to a RichText object
        return StoryText(value)

    def value_from_form(self, value):
        # RichTextArea returns a source-HTML string; concert to a RichText object
        return StoryText(value)

    class Meta:
        classname = 'widget-rich_text_area'

class ImageFormatChoiceBlock(FieldBlock):
    field = forms.ChoiceField(choices=[(format.name, format.label) for format in get_image_formats()])

class ImageBlock(StructBlock):
    image = ImageChooserBlock()
    format = ImageFormatChoiceBlock()
    caption = CharBlock(required=False)
    alt_text = CharBlock(required=False)
    attribution = CharBlock(required=False)

    class Meta:
        icon = "image"
        template = "blog/blocks/imageblock.html"

    def render(self,value):
        template = getattr(self.meta, 'template', None)

        prep_values = self.get_prep_value(value)
        format = get_image_format(value['format'])
        image = value['image']

        # Comes from wagtailimages\formats.py Format.image_to_html
        try:
            rendition = image.get_rendition(format.filter_spec)
        except SourceImageIOError:
            # Image file is (probably) missing from /media/original_images - generate a dummy
            # rendition so that we just output a broken image, rather than crashing out completely
            # during rendering
            Rendition = image.renditions.model  # pick up any custom Image / Rendition classes that may be in use
            rendition = Rendition(image=image, width=0, height=0)
            rendition.file.name = 'not-found'

        if format.classnames:
            class_attr = 'class="%s" ' % escape(format.classnames)
        else:
            class_attr = ''

        value_dict = dict(value)
        value_dict.update({ 'rendition': rendition, 'class_attr': mark_safe(class_attr), 'self': value})
        return render_to_string(template, value_dict)

class PhotoGridBlock(StructBlock):
    images = ListBlock(ImageChooserBlock())

    class Meta:
        icon = "grip"

class PullQuoteBlock(StructBlock):
    quote = CharBlock(classname="quote title")
    attribution = CharBlock()

    class Meta:
        icon = "openquote"

class PullQuoteImageBlock(StructBlock):
    quote = CharBlock()
    attribution = CharBlock()
    image = ImageChooserBlock(required=False)

class StoryBlock(StreamBlock):
    h2 = CharBlock(icon="title", classname="h2 title")
    h3 = CharBlock(icon="title", classname="h3 title")
    h4 = CharBlock(icon="title", classname="h4 title")
    paragraph = StoryTextBlock(icon="pilcrow")
    image = ImageBlock(label="image")
    pullquote = PullQuoteBlock()
    raw_html = RawHTMLBlock(label='Raw HTML', icon="code")
    embed = EmbedBlock(icon="code")

    class Meta:
        template = "blog/blocks/storyblock.html"