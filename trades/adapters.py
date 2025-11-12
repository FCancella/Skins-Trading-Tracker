from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import get_adapter
from django.contrib.auth import get_user_model

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        """
        Intercepta o login social ANTES que ele tente criar um usuário.
        O objetivo é linkar automaticamente se um usuário com o mesmo email
        já existir (conta local).
        """
        # Se a conta social já existe e está linkada, não faz nada.
        # O allauth vai simplesmente logar o usuário.
        if sociallogin.is_existing:
            return

        # Se não veio nenhum email, deixa o allauth pedir.
        if not sociallogin.email_addresses:
            return

        # 1. Pega TODOS os e-mails verificados vindos do Google
        verified_emails = []
        for email_address in sociallogin.email_addresses:
            if email_address.verified: # Confia apenas nos e-mails que o Google diz que são verificados
                verified_emails.append(email_address.email.lower())
        
        if not verified_emails:
            # Se não houver e-mails verificados, não podemos fazer nada.
            return

        User = get_user_model()

        try:
            # 2. Tenta encontrar um usuário local que tenha QUALQUER um desses e-mails
            user = User.objects.get(email__iexact__in=verified_emails)

            # 3. Email existe! O usuário já tem uma conta local.
            # Vamos linkar esta conta social (Google) ao usuário existente.
            sociallogin.connect(request, user)
        
        except User.DoesNotExist:
            # Email não existe. Este é um usuário 100% novo.
            # O allauth vai criar a conta automaticamente
            # graças a SOCIALACCOUNT_AUTO_SIGNUP = True em settings.py
            pass
        
        except User.MultipleObjectsReturned:
            # Cenário raro: Múltiplas contas locais com os e-mails da lista.
            # Não podemos fazer nada automático, então deixamos o allauth falhar.
            pass

    def populate_user(self, request, sociallogin, data):
        """
        (Este é o seu método original, mantido como está)
        Substitui o método padrão para preencher o usuário.
        Nosso objetivo é criar um `username` formatado (ex: "Nome Sobrenome").
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Pega o primeiro nome dos dados do Google
        first_name = data.get('given_name', '')
        
        if first_name:
            # Formata o nome: "Nome".title()
            full_name = f"{first_name}".strip().title()
            
            # Verifica se o nome não está vazio e tenta usá-lo
            if full_name:
                # Usa o 'get_adapter' para encontrar um nome de usuário único
                # Se "Felipe" existir, ele tentará "Felipe 2", etc.
                user.username = get_adapter().generate_unique_username([
                    full_name,
                    user.email,
                    'user'
                ])
                
        # Se 'full_name' falhar, o 'allauth' já terá
        # preenchido o 'username' com uma versão do email, o que é seguro.
        return user