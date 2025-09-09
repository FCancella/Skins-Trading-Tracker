from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib import messages

import mercadopago

from .models import Subscription
from trades.views import _calculate_portfolio_metrics

PLANS = {
    "1": {"name": "1 Mês", "price": 9.99, "days": 30, "is_popular": False},
    "2": {"name": "3 Meses", "price": 12.99, "days": 90, "is_popular": True},
    "3": {"name": "6 Meses", "price": 24.99, "days": 180, "is_popular": False},
}

@login_required
def subscription_details(request: HttpRequest) -> HttpResponse:
    try:
        subscription = request.user.subscription
        if not subscription.is_active:
            return redirect("plans")
    except Subscription.DoesNotExist:
        return redirect("plans")

    return render(request, "subscriptions/subscription_details.html", {"subscription": subscription})


def plans(request: HttpRequest) -> HttpResponse:
    # Lógica para processar planos e descontos (sem alteração)
    base_monthly_price = PLANS["1"]["price"]
    processed_plans = {}
    for plan_id, plan_details in PLANS.items():
        months = plan_details["days"] / 30
        monthly_price = plan_details["price"] / months
        discount = 0
        if months > 1:
            discount = round((1 - (monthly_price / base_monthly_price)) * 100)
        processed_plans[plan_id] = {
            **plan_details,
            "monthly_price": f"{monthly_price:.2f}".replace('.',','),
            "discount": discount,
        }
    
    # Lógica da pré-visualização do portfólio (sem alteração)
    demo_user = User.objects.filter(profile__is_public=True).first()
    portfolio_data = {}
    if demo_user:
        portfolio_data = _calculate_portfolio_metrics(demo_user)

    # Nova lógica para verificar elegibilidade do teste gratuito
    is_eligible_for_trial = True
    if request.user.is_authenticated:
        # Usuário é elegível se nunca teve uma assinatura (nenhum ID de pagamento registrado)
        is_eligible_for_trial = not Subscription.objects.filter(user=request.user, mp_payment_id__isnull=False).exists()


    context = {
        "plans": processed_plans,
        "portfolio_data": portfolio_data,
        "selected_user": demo_user,
        "is_eligible_for_trial": is_eligible_for_trial,
    }
    return render(request, "subscriptions/plans.html", context)

@login_required
def activate_trial(request: HttpRequest) -> HttpResponse:
    """Ativa o teste gratuito de 14 dias para usuários elegíveis."""
    subscription, created = Subscription.objects.get_or_create(user=request.user)

    # Verifica se o usuário já teve alguma assinatura antes
    if Subscription.objects.filter(user=request.user, mp_payment_id__isnull=False).exists():
        messages.error(request, 'O período de teste gratuito já foi utilizado.')
        return redirect('plans')

    subscription.status = 'approved'
    subscription.end_date = timezone.now() + timedelta(days=14)
    # Identificador único para o teste gratuito
    subscription.mp_payment_id = f"TRIAL_{request.user.id}_{timezone.now().timestamp()}"
    subscription.save()
    
    messages.success(request, 'Teste gratuito de 14 dias ativado com sucesso!')
    return redirect('payment_success')


@login_required
def create_payment(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        plan_id = request.POST.get("plan")
        plan = PLANS.get(plan_id)

        if not plan:
            return redirect("plans")

        subscription, created = Subscription.objects.get_or_create(user=request.user)

        # Lógica Padrão do Mercado Pago
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        request.session['pending_plan_id'] = plan_id
        subscription.status = '-'
        subscription.save()

        preference_data = {
            "items": [
                {
                    "title": f"Plano de Assinatura - {plan['name']}",
                    "quantity": 1,
                    "unit_price": plan['price'],
                }
            ],
            "back_urls": {
                "success": request.build_absolute_uri(reverse('payment_success')).replace('http://', 'https://'),
                "failure": request.build_absolute_uri(reverse('payment_failure')).replace('http://', 'https://'),
                "pending": request.build_absolute_uri(reverse('payment_pending')).replace('http://', 'https://'),
            },
            "auto_return": "approved",
            "external_reference": subscription.id,
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        return redirect(preference["init_point"])

    return redirect("plans")

@login_required
def retry_payment(request: HttpRequest) -> HttpResponse:
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    subscription = Subscription.objects.get(user=request.user)

    # 1. Verifica se existe um ID de pagamento anterior
    if subscription.mp_payment_id:
        try:
            # 2. Consulta o status do pagamento no Mercado Pago
            payment_info = sdk.payment().get(subscription.mp_payment_id)
            payment = payment_info.get("response", {})
            
            # 3. Se o pagamento foi aprovado, ativa a assinatura e redireciona
            if payment.get("status") == 'approved':
                subscription.status = 'approved'
                
                # Reutiliza a lógica para encontrar o plano e definir a data de expiração
                plan_name = payment.get("description", "").replace("Plano de Assinatura - ", "")
                for plan_id, plan_details in PLANS.items():
                    if plan_details["name"] == plan_name:
                        subscription.end_date = timezone.now() + timedelta(days=plan_details['days'])
                        break
                
                subscription.save()
                return redirect('payment_success')

        except Exception as e:
            # Se a consulta falhar (ex: pagamento expirado), continua para criar um novo
            print(f"Erro ao consultar pagamento antigo: {e}")
            pass

    # 4. Se o pagamento não foi aprovado ou não existe, cria uma nova preferência
    plan_id = request.session.get('pending_plan_id')
    if not plan_id:
        return redirect('plans')

    # Simula um POST para a view create_payment para gerar um novo link
    request.method = 'POST'
    request.POST = {'plan': plan_id}
    return create_payment(request)


@csrf_exempt
def mp_webhook(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        data = request.GET.dict()
        if data.get("type") == "payment":
            payment_id = data.get("data.id")
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info["response"]

            subscription_id = payment.get("external_reference")
            if subscription_id:
                subscription = Subscription.objects.get(id=subscription_id)
                subscription.mp_payment_id = payment.get("id")
                subscription.status = payment.get("status")

                if subscription.status == 'approved':
                    # Limpa o ID do plano pendente da sessão
                    if 'pending_plan_id' in request.session:
                        del request.session['pending_plan_id']

                    plan_name = None
                    if payment.get("description"):
                        description = payment.get("description")
                        if "Plano de Assinatura - " in description:
                            plan_name = description.replace("Plano de Assinatura - ", "")

                    if plan_name:
                        for id, plan_details in PLANS.items():
                            if plan_details["name"] == plan_name:
                                subscription.end_date = timezone.now() + timedelta(days=plan_details['days'])
                                break
                
                subscription.save()

    return HttpResponse(status=200)

@login_required
def payment_success(request: HttpRequest) -> HttpResponse:
    return render(request, "subscriptions/payment_success.html")

@login_required
def payment_failure(request: HttpRequest) -> HttpResponse:
    return render(request, "subscriptions/payment_failure.html")

@login_required
def payment_pending(request: HttpRequest) -> HttpResponse:
    return render(request, "subscriptions/payment_pending.html")