#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf import settings


DEFAULT_SETTINGS = {
    "DATE_FORMAT": "%Y/%b/", # end with trailing slash.
    "DATE_FUNCTION": 'title', # upper, lower
}

USER_SETTINGS = DEFAULT_SETTINGS.copy()
USER_SETTINGS.update(getattr(settings, 'BLOG_SETTINGS', {}))

globals().update(USER_SETTINGS)
