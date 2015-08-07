from wagtail.wagtailcore import hooks
from django.utils.html import format_html, format_html_join
from django.conf import settings

@hooks.register('insert_editor_js')
def editor_js():
    return """
        <script>
            halloPlugins = {
                halloformat: {formattings: {
                  bold: true,
                  italic: true,
                  strikeThrough: false,
                  underline: false
                }},
                halloheadings: {formatBlocks: ['p']},
                hallolists: {},
                halloreundo: {},
                hallowagtaillink: {},
                hallorequireparagraphs: {blockElements: ['p','ol','ul']}
            };
        </script>
    """