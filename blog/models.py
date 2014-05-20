#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings as site_settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import ugettext, ugettext_lazy as _

from django.contrib.contenttypes.models import ContentType

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

from datetime import datetime

if settings.USE_TAGS:
    class BlogPostTag(TaggedItemBase):
        content_object = ParentalKey('blog.BlogPost', related_name='tagged_items')

class BlogPost(Page):
    content = RichTextField(blank=True)
    date = models.DateField(help_text="The date used while organizing the posts",default=datetime.now())

    if settings.USE_FEATURED_IMAGES:
        featured_image = models.ForeignKey(Image, related_name='+', blank=True, null=True)

    if settings.USE_CATEGORIES:
        category = models.ForeignKey('blog.BlogCategory', related_name='blog_posts', blank=True, null=True)

    if settings.USE_TAGS:
        tags = ClusterTaggableManager(through='blog.BlogPostTag', blank=True)

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
            # Raise an error?
            self.url_path = '/'

BlogPost.content_panels = [] + Page.content_panels # need to copy the list, not alias it

if settings.USE_FEATURED_IMAGES:
    BlogPost.content_panels += [
        ImageChooserPanel('featured_image'),
    ]

BlogPost.content_panels += [
    FieldPanel('date'),
    FieldPanel('content'),
]

if settings.USE_CATEGORIES:
    BlogPost.content_panels += [ PageChooserPanel('category', 'blog.BlogCategory'), ]

if settings.USE_TAGS:
    BlogPost.promote_panels = Page.promote_panels + [ FieldPanel('tags'), ]

class BlogIndexBase(Page):
    is_abstract = True

    template = "blog/blog_index.html"

    def get_context(self, request):
        # Get blogs
        posts = self.get_posts(request)

        # Filter by tag
        tag = request.GET.get('tag')
        if tag:
            posts = posts.filter(tags__name=tag)

        # Pagination
        page = request.GET.get('page')
        paginator = Paginator(posts, settings.POSTS_PER_PAGE)
        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            posts = paginator.page(1)
        except EmptyPage:
            posts = paginator.page(paginator.num_pages)

        # Update template context
        context = super(BlogIndexBase,self).get_context(request)
        context['posts'] = posts
        return context

    class Meta:
        abstract = True


class BlogType(BlogIndexBase):
    subpage_types = ['blog.BlogPost']
    if settings.USE_CATEGORIES:
        subpage_types += ['blog.BlogCategory']
    template = BlogIndexBase.template

    def route(self, request, path_components):
        if path_components:
            # request is for a child of this page
            child_path = '/'.join(path_components+[''])

            try: # try posts or first level categories
                subpage = self.get_children().get(url_path=self.url_path+child_path)
            except Page.DoesNotExist: # use Page's route to get deeper categories
                return super(BlogType,self).route(request,path_components)

            return subpage.specific.route(request, None)

        else:
            # request is for this very page
            if self.live:
                return self.serve(request)
            else:
                raise Http404

    def get_posts(self, request):
        return BlogPost.objects.filter(id__in=self.get_children()).order_by('-date')

if settings.USE_CATEGORIES:
    class BlogCategory(BlogIndexBase):
        subpage_types = ['blog.BlogCategory']
        template = BlogIndexBase.template

        def get_posts(self, request):
            return BlogPost.objects.filter(id__in=self.get_parent().get_children(),category=self).order_by('-date')