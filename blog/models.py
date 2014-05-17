#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings as site_settings
from django.utils.translation import ugettext, ugettext_lazy as _

from blog import settings

from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailadmin.edit_handlers import FieldPanel, MultiFieldPanel, \
    InlinePanel, PageChooserPanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailimages.models import Image
from wagtail.wagtaildocs.edit_handlers import DocumentChooserPanel
from wagtail.wagtailsnippets.edit_handlers import SnippetChooserPanel
from wagtail.wagtailsnippets.models import register_snippet

from modelcluster.fields import ParentalKey
from modelcluster.tags import ClusterTaggableManager
from taggit.models import Tag, TaggedItemBase


class BlogPost(Page):
    content = RichTextField(blank=True)
    date = models.DateField(help_text="The date used while organizing the posts")

    def set_url_path(self, parent):
        """
        Populate the url_path field based on this page's slug and the specified parent page.
        (We pass a parent in here, rather than retrieving it via get_parent, so that we can give
        new unsaved pages a meaningful URL when previewing them; at that point the page has not
        been assigned a position in the tree, as far as treebeard is concerned.
        """
        if parent:
            self.url_path = parent.url_path + getattr(self.date.strftime(settings.DATE_FORMAT),settings.DATE_FUNCTION)() + self.slug + '/'
        else:
            # a page without a parent is the tree root, which always has a url_path of '/'
            self.url_path = '/'

BlogPost.content_panels = [
    FieldPanel('title', classname="full title"),
    FieldPanel('content'),
    FieldPanel('date'),
]

class BlogType(Page):
    subpage_types = ['blog.BlogPost']

    def route(self, request, path_components):
        if path_components:
            # request is for a child of this page
            child_path = '/'.join(path_components+[''])

            try:
                subpage = self.get_children().get(url_path=self.url_path+child_path)
            except Page.DoesNotExist:
                raise Http404

            return subpage.specific.route(request, None)

        else:
            # request is for this very page
            if self.live:
                return self.serve(request)
            else:
                raise Http404