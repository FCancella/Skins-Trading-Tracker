# trades/templatetags/form_extras.py
from django import template
register = template.Library()

@register.filter
def add_class(field, css_classes_to_add):
    """Adiciona classes CSS a um campo de formulário sem remover as existentes."""
    # Pega todos os atributos existentes do widget do campo
    all_attrs = field.field.widget.attrs.copy() or {}
    
    # Pega as classes que já existem no campo
    existing_classes = all_attrs.get('class', '')
    
    # Combina as classes existentes com as novas, garantindo que não haja espaços duplos
    all_attrs['class'] = f'{existing_classes} {css_classes_to_add}'.strip()
    
    # Retorna o campo renderizado com os atributos atualizados
    return field.as_widget(attrs=all_attrs)