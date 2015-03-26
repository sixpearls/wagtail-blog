#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.test import TestCase


class blogTest(TestCase):
    """
    Tests for blog
    """
    fixtures = ['test_data.json']
    # with testdata, we should get...
    # >>> len(Page.objects.listable(User.objects.get(pk=2)))
    # 9
    # >>> len(Page.objects.listable(User.objects.get(pk=1)))
    # 10
    # >>> len(Page.objects.viewable(User.objects.get(pk=1)))
    # 10
    # >>> len(Page.objects.viewable(User.objects.get(pk=2)))

    def test_blog(self):
        pass
