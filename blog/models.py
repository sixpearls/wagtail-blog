#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings as site_settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import ugettext, ugettext_lazy as _
from django.http import QueryDict
from django.utils.safestring import mark_safe

from django.contrib.contenttypes.models import ContentType

from blog import settings

from wagtail.wagtailcore.models import Page
from wagtail.wagtailcore.url_routing import RouteResult
from wagtail.wagtailcore.fields import RichTextField, StreamField

from .blocks import StoryBlock

from wagtail.wagtailadmin.edit_handlers import FieldPanel, PageChooserPanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailimages.models import Image

from modelcluster.fields import ParentalKey
from modelcluster.tags import ClusterTaggableManager
from taggit.models import Tag, TaggedItemBase

from datetime import datetime

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


CONTEXT_POST_QUERYSTRING_KEY = 'post_url_querystring'
CONTEXT_PAGE_QUERYSTRING_KEY = 'page_url_querystring'

if settings.USE_TAGS:
    class BlogPostTag(TaggedItemBase):
        content_object = ParentalKey('blog.BlogPost', related_name='tagged_items')

def update_context_querystring(context,context_key,first_arg=True,**kwargs):
    query = QueryDict(urlparse(context.get(context_key,'')).query).copy()
    query.update(kwargs)
    if first_arg:
        lead_char = '?'
    else:
        lead_char = '&'
    if query:
        context[context_key] = mark_safe(lead_char + query.urlencode())
    return context

class BlogPost(Page):
    date = models.DateField(help_text="The date used while organizing the posts",default=datetime.now())
    if 'wagtail.contrib.wagtailapi' in site_settings.INSTALLED_APPS:
        api_fields = ('date',)

    if settings.USE_STREAMFIELD:
        content = StreamField(StoryBlock())

        @property
        def rendered_content(self):
            return self.content.__str__()

        if 'wagtail.contrib.wagtailapi' in site_settings.INSTALLED_APPS:
            api_fields += ('rendered_content',)
            pass

    else:
        content = RichTextField(blank=True)

    if settings.USE_FEATURED_IMAGES:
        featured_image = models.ForeignKey(Image, related_name='+', blank=True, null=True, on_delete=models.SET_NULL)

        if 'wagtail.contrib.wagtailapi' in site_settings.INSTALLED_APPS:
            api_fields += ('featured_image',)

    if settings.USE_CATEGORIES:
        category = models.ForeignKey('blog.BlogCategory', related_name='blog_posts', blank=True, null=True, on_delete=models.SET_NULL)

        if 'wagtail.contrib.wagtailapi' in site_settings.INSTALLED_APPS:
            api_fields += ('category',)

    if settings.USE_TAGS:
        tags = ClusterTaggableManager(through='blog.BlogPostTag', blank=True)

        if 'wagtail.contrib.wagtailapi' in site_settings.INSTALLED_APPS:
            api_fields += ('tags',)


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

    def get_siblings(self, inclusive=True):
        return BlogPost.objects.sibling_of(self, inclusive).live().order_by('-date')

    def get_context(self, request):
        context = super(BlogPost, self).get_context(request)
        siblings = self.get_siblings()

        tag = None
        category = None
        if settings.USE_TAGS:
            tag = request.GET.get('tag')
        if settings.USE_CATEGORIES:
            category = request.GET.get('category')

        if tag:
            siblings = siblings.filter(tags__name=tag)
            update_context_querystring(context,CONTEXT_POST_QUERYSTRING_KEY,first_arg=True,tag=tag)
        elif category:
            siblings = siblings.filter(category__slug=category)
            update_context_querystring(context,CONTEXT_POST_QUERYSTRING_KEY,first_arg=True,category=category)

        ids = [obj.pk for obj in siblings]
        if self.pk in ids:
            idx = ids.index(self.pk)
            if idx < len(siblings) - 1:
                context['next_post'] = siblings[idx + 1]
            if idx > 0:
                context['prev_post'] = siblings[idx - 1]
        return context

BlogPost.content_panels = [] + Page.content_panels # need to copy the list, not alias it

if settings.USE_FEATURED_IMAGES:
    BlogPost.content_panels += [
        ImageChooserPanel('featured_image'),
    ]

BlogPost.content_panels += [
    FieldPanel('date'),
]

if settings.USE_STREAMFIELD:
    from wagtail.wagtailadmin.edit_handlers import StreamFieldPanel
    BlogPost.content_panels += [ StreamFieldPanel('content'), ]
else:
    BlogPost.content_panels += [ FieldPanel('content', classname="full"), ]

if settings.USE_CATEGORIES:
    BlogPost.content_panels += [ PageChooserPanel('category', 'blog.BlogCategory'), ]

if settings.USE_TAGS:
    BlogPost.promote_panels = Page.promote_panels + [ FieldPanel('tags'), ]

class BlogIndexBase(Page):
    is_abstract = True

    template = "blog/blog_index.html"

    def get_context(self, request):
        context = super(BlogIndexBase,self).get_context(request)
        posts = self.get_posts(request)

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
        context['posts'] = posts
        return context

    # TODO: filter posts that have private tag, type, or category
    def get_posts(self, request=None):
        return BlogPost.objects.descendant_of(self, False).live().order_by('-date')

    class Meta:
        abstract = True

class BlogType(BlogIndexBase):
    subpage_types = ['blog.BlogPost']
    if settings.USE_CATEGORIES:
        subpage_types += ['blog.BlogCategory']
    template = BlogIndexBase.template

    if settings.USE_TAGS:
        def get_posts(self, request=None):
            posts = super(BlogType,self).get_posts(request)
            tag = request.GET.get('tag')
            if tag:
                posts = posts.filter(tags__name=tag)
            return posts

        def get_context(self, request):
            context = super(BlogType,self).get_context(request)
            tag = request.GET.get('tag')
            if tag:
                update_context_querystring(context,CONTEXT_PAGE_QUERYSTRING_KEY,first_arg=False,tag=tag)
                update_context_querystring(context,CONTEXT_POST_QUERYSTRING_KEY,first_arg=True,tag=tag)
            return context

    def route(self, request, path_components):
        # TODO: possibly better to use routable mix-in. Also may be better if this handles routing for (child) categories?
        # also need to create month/day logic.
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
                return RouteResult(self)
            else:
                raise Http404

if settings.USE_CATEGORIES:
    class BlogCategory(BlogIndexBase):
        subpage_types = ['blog.BlogCategory']
        template = BlogIndexBase.template

        def get_context(self, request):
            context = super(BlogCategory,self).get_context(request)
            update_context_querystring(context,CONTEXT_POST_QUERYSTRING_KEY,first_arg=True,category=self.slug)
            return context

        def get_posts(self, request=None):
            return BlogPost.objects.filter(category=self).live().order_by('-date')

class AjaxBlogPage(Page):
    blog_page = models.ForeignKey(BlogType, related_name='ajax_user', blank=True, null=True, on_delete=models.SET_NULL)

    def route(self, request, path_components):
        result = super(AjaxBlogPage,self).route(request,path_components)
        if isinstance(result, RouteResult):
            result_page = result[0]
            if result_page == self.blog_page or result_page == self or self.blog_page.get_descendants().filter(id__in=[result_page.id]).exists():
                return RouteResult(self,kwargs={'true_request_page': result_page})
        return result

    def get_context(self, request, *args, **kwargs):
        true_request_page = kwargs.pop('true_request_page', None)
        context = super(AjaxBlogPage, self).get_context(request, *args, **kwargs)
        if true_request_page:
            tag = None
            category = None
            if settings.USE_TAGS:
                tag = request.GET.get('tag')
            if settings.USE_CATEGORIES:
                if isinstance(true_request_page, BlogCategory):
                    category = true_request_page
                else:
                    category = request.GET.get('category') 

            if isinstance(true_request_page, BlogPost):
                siblings = true_request_page.get_siblings()

            if tag:
                update_context_querystring(context,CONTEXT_POST_QUERYSTRING_KEY,first_arg=False,tag=tag)
                if isinstance(true_request_page, BlogPost):
                    siblings = siblings.filter(tags__name=tag)
                context['taxonomy_name'] = 'tags'
                context['taxonomy_value'] = tag
            elif category:
                update_context_querystring(context,CONTEXT_POST_QUERYSTRING_KEY,first_arg=False,category=category)
                if isinstance(true_request_page, BlogPost):
                    siblings = siblings.filter(category__slug=category)
                context['taxonomy_name'] = 'category'
                context['taxonomy_value'] = category

            if isinstance(true_request_page, BlogPost):
                for i, x in enumerate(siblings):
                    if x == true_request_page:
                        offset = i
            else:
                offset = 0

            context['offset'] = offset
            context['limit'] = settings.POSTS_PER_PAGE

            return context

        else:
            raise Http404 #How did I get here?

AjaxBlogPage.content_panels = Page.content_panels + [ PageChooserPanel('blog_page', 'blog.BlogType'), ]