# trades/templatetags/form_extras.py
from django import template
register = template.Library()

@register.filter
def add_class(field, css_classes_to_add):
    """
    Adiciona classes CSS a um campo de formulário.
    Modo de segurança: se o 'field' não for um objeto de campo válido,
    ele retorna o valor original sem falhar.
    """
    
    # VERIFICAÇÃO DE SEGURANÇA:
    # Se o 'field' não tiver o método 'as_widget' (ex: for um string),
    # apenas retorna o valor original sem fazer nada e sem quebrar a página.
    if not hasattr(field, 'as_widget'):
        return field

    # Tenta pegar os atributos do widget.
    # A maioria dos BoundFields terá 'widget.attrs'.
    try:
        all_attrs = field.widget.attrs.copy()
    except AttributeError:
        # Como fallback, tenta o caminho mais longo (comum em ModelForms)
        try:
            all_attrs = field.field.widget.attrs.copy()
        except AttributeError:
            # Se tudo falhar, começa do zero
            all_attrs = {}

    existing_classes = all_attrs.get('class', '')
    all_attrs['class'] = f'{existing_classes} {css_classes_to_add}'.strip()
    
    return field.as_widget(attrs=all_attrs)