from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Store, StoreItem
from .forms import StoreSettingsForm
from .utils import get_steam_inventory, get_item_base_price

@login_required
def manage_store(request):
    store, created = Store.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'update_settings' in request.POST:
            form = StoreSettingsForm(request.POST, instance=store)
            if form.is_valid():
                form.save()
                messages.success(request, 'Configurações da loja atualizadas!')
                return redirect('manage_store')
        
        elif 'refresh_inventory' in request.POST:
            if not store.steam_id:
                messages.error(request, 'Configure seu Steam ID primeiro.')
            else:
                inventory_data = get_steam_inventory(store.steam_id)
                
                if inventory_data:
                    store.items.all().delete()
                    
                    new_items = []
                    for item_data in inventory_data:
                        name = item_data['name']
                        image = item_data['image']
                        item_type = item_data.get('type', '')
                        
                        # Busca apenas o preço base
                        base_price = get_item_base_price(name)
                        
                        if base_price > 0:
                            is_auto_hidden = any(keyword in item_type for keyword in ['Sticker', 'Container', 'Case'])
                            
                            new_items.append(StoreItem(
                                store=store,
                                name=name,
                                image_url=image,
                                base_price=base_price,
                                is_visible=not is_auto_hidden
                            ))
                    
                    StoreItem.objects.bulk_create(new_items)
                    
                    count = len(new_items)
                    ignored = len(inventory_data) - count
                    messages.success(request, f'{count} itens importados. ({ignored} ignorados por preço baixo).')
                else:
                    messages.error(request, 'Não foi possível buscar o inventário. Verifique o Steam ID ou se o inventário é público.')
            return redirect('manage_store')

        elif 'update_items' in request.POST:
            items = store.items.all()
            for item in items:
                # 1. Atualiza Visibilidade
                is_visible = request.POST.get(f'visible_{item.id}') == 'on'
                item.is_visible = is_visible

                # 2. Atualiza Preço Base (Editável)
                new_price_str = request.POST.get(f'base_price_{item.id}')
                if new_price_str:
                    try:
                        # Remove R$ e espaços, troca vírgula por ponto se necessário
                        clean_price = new_price_str.replace('R$', '').replace(' ', '').replace(',', '.')
                        item.base_price = Decimal(clean_price)
                    except Exception:
                        pass # Mantém o valor antigo se o input for inválido

                item.save()
                
            messages.success(request, 'Itens atualizados com sucesso!')
            return redirect('manage_store')

    else:
        form = StoreSettingsForm(instance=store)

    # Ordenação por base_price, pois price agora é calculado
    items = store.items.all().order_by('-base_price')
    
    return render(request, 'stores/manage_store.html', {
        'form': form, 
        'items': items,
        'store': store
    })

def public_store(request, username):
    user = get_object_or_404(User, username=username)
    store = get_object_or_404(Store, user=user)
    
    items = store.items.filter(is_visible=True).order_by('-base_price')
    
    return render(request, 'stores/public_store.html', {
        'store_owner': user,
        'store': store,
        'items': items
    })