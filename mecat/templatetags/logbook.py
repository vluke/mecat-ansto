from django import template
from tardis.tardis_portal.models import Dataset_File

register = template.Library()


class LogBooksNode(template.Node):
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        try:
            log_books = Dataset_File.objects.filter(
                    dataset__experiment=context['experiment'],
                    dataset__description__exact='Log Books')
            context[self.varname] = log_books[0]
        except:
            pass
        return ''


@register.tag
def get_log_book(parser, token):
    args = token.split_contents()
    if len(args) != 3:
        raise TemplateSyntaxError, 'get_log_book tag takes exactly two arguments'
    if args[1] != 'as':
        raise TemplateSyntaxError, 'first argument to get_log_book must be "as"'
    return LogBooksNode(args[2])

