#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings as site_settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import ugettext, ugettext_lazy as _
from django.http import QueryDict
from django.utils.safestring import mark_safe
from django.contrib.auth.models import Group

from blog import settings

from wagtail.wagtailcore.models import Page, PageManager
from wagtail.wagtailcore.url_routing import RouteResult
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailadmin.edit_handlers import FieldPanel, FieldRowPanel, \
    InlinePanel, PageChooserPanel, BaseChooserPanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtailimages.models import Image

from modelcluster.fields import ParentalKey
from modelcluster.tags import ClusterTaggableManager
from taggit.models import Tag, TaggedItemBase

from datetime import datetime
from urlparse import urlparse

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

    if settings.USE_STREAM_FIELD:
        pass
    else:
        content = RichTextField(blank=True)

    if settings.USE_FEATURED_IMAGES:
        featured_image = models.ForeignKey(Image, related_name='+', blank=True, null=True, on_delete=models.SET_NULL)

    if settings.USE_CATEGORIES:
        category = models.ForeignKey('blog.BlogCategory', related_name='blog_posts', blank=True, null=True, on_delete=models.SET_NULL)

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

    def get_siblings(self, inclusive=True):
        return BlogPost.objects.sibling_of(self, inclusive).live().order_by('-date')

    def get_context(self, request):
        context = super(BlogPost, self).get_context(request)
        siblings = self.get_siblings()
        #TODO: some kind of view restriction filter

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

    def check_restrictions(self,user=None):
        return self in Page.objects.viewable(user)

    # TODO: validate category is of same type as post
    # TODO: validate group authorization is stricter than inherited group authorization?

BlogPost.content_panels = [] + Page.content_panels # need to copy the list, not alias it

if settings.USE_FEATURED_IMAGES:
    BlogPost.content_panels += [
        ImageChooserPanel('featured_image'),
    ]

BlogPost.content_panels += [
    FieldPanel('date'),
    FieldPanel('content', classname="full"),
]

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

    def serve_restricted_view(self):
        return

    # TODO: filter posts that have a restriction or have restricted type/category
    def get_posts(self, request=None):
        posts = BlogPost.objects.descendant_of(self, False).live().order_by('-date')
        user = None
        if request.user.is_authenticated():
            user = request.user
        posts = posts.listable(user)
        return posts

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
            posts = BlogPost.objects.filter(category=self).live().order_by('-date')
            user = None
            if request.user.is_authenticated():
                user = request.user
            posts = posts.listable(user)
            return posts

class BaseGroupChooserPanel(BaseChooserPanel):
    object_type_name = "group"

class GroupChooserPanel(object):
    def __init__(self, field_name, page_type=None):
        self.field_name = field_name

    def bind_to_model(self, model):
        return type(str('_GroupChooserPanel'), (BaseGroupChooserPanel,), {
            'model': model,
            'field_name': self.field_name,
        })

# TODO: admin interface shows inherited group view restriction
# TODO: customizable group view restriction interface

class PageGroupViewRestriction(models.Model):
    page = ParentalKey('wagtailcore.Page', related_name='view_groups')
    permitted_group = models.ForeignKey(Group, related_name='page_view_authorization')
    completely_hidden = models.BooleanField(default=False, help_text=_('Check to prevent users not in the permitted group from seeing this at all'))

Page.settings_panels += [
    InlinePanel('view_groups',label="Restrict view to the following groups",
        panels = [
            GroupChooserPanel('permitted_group'),
            FieldPanel('completely_hidden'),
    ]),
]



def build_ancestor_queue(pages):
    ancestorQ = models.Q()
    for page in pages:
        ancestorQ = ancestorQ|models.Q(path__startswith=page.path)
    return ancestorQ

def explicit_unlistable(self,user=None):
    unlistable_pages = self.get_queryset().filter(view_groups__completely_hidden=True)
    if user is not None:
        unlistable_pages = unlistable_pages.exclude(view_groups__permitted_group__in=user.groups.all())
    return unlistable_pages.distinct()

def explicit_unviewable(self,user=None):
    unviewable_pages = self.get_queryset().filter(view_groups__isnull=False)
    if user is not None:
        unviewable_pages = unviewable_pages.exclude(view_groups__permitted_group__in=user.groups.all())
    return unviewable_pages.distinct()

def listable(self,user=None):
    unlistable_pages = Page.objects.explicit_unlistable(user)
    ancestorQ = build_ancestor_queue(unlistable_pages)
    return self.get_queryset().exclude(ancestorQ)

def unlistable(self,user=None):
    unlistable_pages = Page.objects.explicit_unlistable(user)
    ancestorQ = build_ancestor_queue(unlistable_pages)
    return self.get_queryset().filter(ancestorQ)

def viewable(self,user=None):
    unviewable_pages = Page.objects.explicit_unviewable(user)
    ancestorQ = build_ancestor_queue(unviewable_pages)
    return self.get_queryset().exclude(ancestorQ)

def unviewable(self,user=None):
    unviewable_pages = Page.objects.explicit_unviewable(user)
    ancestorQ = build_ancestor_queue(unviewable_pages)
    return self.get_queryset().filter(ancestorQ)

PageManager.explicit_unlistable = explicit_unlistable
PageManager.explicit_unviewable = explicit_unviewable

PageManager.listable = listable
PageManager.viewable = viewable

PageManager.unlistable = unlistable
PageManager.unviewable = unviewable