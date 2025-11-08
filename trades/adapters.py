from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import get_adapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def populate_user(self, request, sociallogin, data):
        """
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