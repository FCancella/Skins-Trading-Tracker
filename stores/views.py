import json
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
from .models import Store, StoreItem, StoreLog
from .forms import StoreSettingsForm
from .utils import get_steam_inventory, get_item_base_price


def _perform_inventory_refresh(store, user, inventory_data):
    """
    Executa a importação em background, salvando item por item
    para permitir que o usuário veja o progresso ao atualizar a página.
    """
    try:
        # 1. Limpa o inventário antigo imediatamente
        store.items.all().delete()
        
        count = 0
        ignored = 0
        total_items = len(inventory_data)
        
        # 2. Processa e SALVA um por um
        for item_data in inventory_data:
            name = item_data['name']
            image = item_data['image']
            item_type = item_data.get('type', '')
            
            # Busca preço (pode demorar um pouco, simulando o delay)
            base_price = get_item_base_price(name)
            
            if base_price > 0:
                is_auto_hidden = any(keyword in item_type for keyword in ['Sticker', 'Container', 'Case'])
                
                # [ALTERAÇÃO] Cria e salva imediatamente no DB
                StoreItem.objects.create(
                    store=store,
                    name=name,
                    image_url=image,
                    base_price=base_price,
                    is_visible=not is_auto_hidden
                )
                count += 1
            else:
                ignored += 1
        
        # LOG de SUCESSO ao finalizar tudo
        StoreLog.objects.create(
            store=store,
            user=user,
            action="Carregar/Reset Inventário (BG)",
            details=f"Finalizado. Importados: {count}, Ignorados: {ignored}"
        )

    except Exception as e:
        # LOG de ERRO
        try:
            StoreLog.objects.create(
                store=store,
                user=user,
                action="Carregar/Reset Inventário (BG)",
                details=f"Erro na thread: {str(e)}"
            )
        except:
            pass


@login_required
def manage_store(request):
    store, created = Store.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        # 1. Atualizar Configurações
        if 'update_settings' in request.POST:
            form = StoreSettingsForm(request.POST, instance=store)
            if form.is_valid():
                form.save()
                # LOG
                StoreLog.objects.create(
                    store=store,
                    user=request.user,
                    action="Salvar Configurações",
                    details=f"Nome: {store.name}, Taxa: {store.fee_percentage}%"
                )
                messages.success(request, 'Configurações da loja atualizadas!')
                return redirect('manage_store')

        # 3. Salvar Alterações Manuais (Itens)
        elif 'update_items' in request.POST:
            items = store.items.all()
            count_updated = 0
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
                count_updated += 1
            
            # LOG
            StoreLog.objects.create(
                store=store,
                user=request.user,
                action="Salvar Itens Manuais",
                details=f"Atualizou visibilidade/preço de {count_updated} itens."
            )
                
            messages.success(request, 'Itens atualizados com sucesso!')
            return redirect('manage_store')

    else:
        form = StoreSettingsForm(instance=store)

    items = store.items.all().order_by('-base_price')
    
    return render(request, 'stores/manage_store.html', {
        'form': form, 
        'items': items,
        'store': store
    })

# [+] NOVA VIEW PARA O REFRESH ASSÍNCRONO
@login_required
@require_POST
def start_refresh_inventory(request):
    store = get_object_or_404(Store, user=request.user)

    if not store.steam_id:
        return JsonResponse({
            'status': 'error', 
            'message': 'Configure seu Steam ID primeiro.'
        }, status=400)
    
    # 1. Busca os dados do inventário primeiro
    inventory_data = get_steam_inventory(store.steam_id)
    
    if inventory_data:
        item_count = len(inventory_data)
        # 2. Calcula a estimativa
        estimated_time_seconds = round(item_count * 2.5, 1)

        # 3. Inicia a thread para fazer o trabalho pesado em background
        thread = threading.Thread(
            target=_perform_inventory_refresh, 
            args=(store, request.user, inventory_data)
        )
        thread.start()

        # LOG de INÍCIO
        StoreLog.objects.create(
            store=store,
            user=request.user,
            action="Início Carregar Inventário",
            details=f"Iniciando {item_count} itens. Estimativa: {estimated_time_seconds}s"
        )

        # 4. Retorna imediatamente o JSON com a estimativa
        return JsonResponse({
            'status': 'ok',
            'item_count': item_count,
            'estimated_time': estimated_time_seconds
        })
    else:
        # Erro ao buscar inventário
        return JsonResponse({
            'status': 'error',
            'message': 'Não foi possível buscar o inventário. Verifique o Steam ID ou se o inventário é público.'
        }, status=400)


def public_store(request, username):
    user = get_object_or_404(User, username=username)
    store = get_object_or_404(Store, user=user)
    
    items = store.items.filter(is_visible=True).order_by('-base_price')
    
    return render(request, 'stores/public_store.html', {
        'store_owner': user,
        'store': store,
        'items': items
    })

@require_POST
def log_cart_checkout(request):
    """Recebe os dados do carrinho via JS e salva o log."""
    try:
        data = json.loads(request.body)
        store_id = data.get('store_id')
        items = data.get('items', [])
        total = data.get('total', 0)

        store = get_object_or_404(Store, id=store_id)
        
        # Formata a lista de itens para salvar no texto
        items_str = ", ".join([f"{i['name']} (R$ {i['price']})" for i in items])
        details_text = f"Total: R$ {total}\nItens: {items_str}"

        # Identifica usuário se estiver logado
        user = request.user if request.user.is_authenticated else None

        StoreLog.objects.create(
            store=store,
            user=user,
            action="Finalizar Pedido (WhatsApp)",
            details=details_text
        )
        
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)