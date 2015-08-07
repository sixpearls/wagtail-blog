#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf import settings


DEFAULT_SETTINGS = {
    "DATE_FORMAT": "%Y/%b/", # end with trailing slash.
    "DATE_FUNCTION": 'title', # upper, lower
    "USE_CATEGORIES": True,
    "USE_TAGS": True,
    "USE_FEATURED_IMAGES": True,
    "POSTS_PER_PAGE": 10,
    "USE_STREAMFIELD": False
}

USER_SETTINGS = DEFAULT_SETTINGS.copy()
USER_SETTINGS.update(getattr(settings, 'BLOG_SETTINGS', {}))

globals().update(USER_SETTINGS)
