from django import template

from mecat.embargo import EmbargoHandler

register = template.Library()

@register.inclusion_tag('inclusion_tags/expiry_editing.html')
def embargo_edit(experiment_id):
    handler = EmbargoHandler(experiment_id)
    inclusion_context = {'experiment_id': experiment_id}
    if handler.never_expires():
        inclusion_context['never_expires'] = True
        inclusion_context['because_no_end_date'] = handler.because_no_end_date()
    elif handler.has_any_expiry():
        inclusion_context['has_any_expiry'] = True
        inclusion_context['expiry_date'] = handler.get_expiry_date().strftime('%Y/%m/%d')
    else:
        raise Exception('unknown state - should never get here')
    inclusion_context['can_be_defaulted'] = handler.can_be_defaulted()

    return inclusion_context
