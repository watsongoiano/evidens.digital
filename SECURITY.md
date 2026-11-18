# Segurança

## Versão coberta

Só a versão publicada em [evidens.life](https://evidens.life), que corresponde à branch `main`, recebe correções.
Não há versões antigas mantidas.

## Como relatar uma vulnerabilidade

Não abra uma issue pública. Use um destes caminhos:

1. **Relato privado no GitHub:** aba *Security* do repositório → *Report a vulnerability*
   ([link direto](https://github.com/watsongoiano/evidens.digital/security/advisories/new)).
2. **Contato do site:** a página [evidens.life/contact](https://evidens.life/contact), pedindo um canal privado
   antes de enviar os detalhes.

Inclua o que for possível: o que a falha permite, os passos para reproduzir, a página ou rota afetada e a data
do teste.

## Ao testar

- Use apenas a sua própria conta e dados fictícios. Não acesse, altere nem apague dados de outros usuários.
- Não envie dados reais de pacientes.
- Não faça testes de carga nem de negação de serviço.
- Dê tempo para a correção antes de divulgar.

## O que o sistema guarda

Para orientar o que é relevante relatar:

- **Contas:** e-mail, nome, registro profissional, senha (só o hash), aceite dos Termos de Uso, eventos de uso
  e as tentativas de login que falharam (e-mail e IP), apagadas ao fim da janela de bloqueio.
- **Do médico:** receituário ou timbrado, credenciamentos em planos de saúde, vínculos com estabelecimentos do
  SUS e, enquanto durar a sessão de assinatura digital, o token dela (cifrado), o certificado público e o nome
  do titular.
- **Do paciente:** nada é gravado. Os dados do formulário e os laudos em PDF são processados em memória e
  descartados; o nome do paciente é opcional e só acompanha o pedido de PDF.

Os perigos clínicos conhecidos e os controles de cada um estão em
[`docs/registro-de-perigos.md`](docs/registro-de-perigos.md). As variáveis de ambiente e os segredos estão
descritos em [`docs/deploy.md`](docs/deploy.md); os segredos ficam só nas variáveis de ambiente.
