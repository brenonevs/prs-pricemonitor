import requests
from lxml import html

# URL da página que você quer raspar
url = 'https://www.carrefour.com.br/iphone-14-apple-128gb-branco-5g-tela-de-6-1polegadas-e-camera-dupla-de-12-mp-3091546/p'

# Fazendo a requisição GET para o URL
response = requests.get(url)

# Verificando se a requisição foi bem sucedida
if response.status_code == 200:
    # Obtendo o conteúdo da página
    page_content = response.text

    # Aqui você pode continuar com a raspagem usando lxml ou outra biblioteca de sua escolha
    # Por exemplo, para usar lxml:
    tree = html.fromstring(page_content)

    # Obtendo o valor inteiro do preço
    preco_inteiro = tree.xpath("//div[contains(@class, 'carrefourbr-carrefour-components-0-x-sellingPriceValue')]//span[contains(@class, 'carrefourbr-carrefour-components-0-x-currencyInteger')]/text()")

    # Obtendo os centavos do preço
    centavos = tree.xpath("//div[contains(@class, 'carrefourbr-carrefour-components-0-x-sellingPriceValue')]//span[contains(@class, 'carrefourbr-carrefour-components-0-x-currencyFraction')]/text()")

    # Concatenando para obter o preço completo
    preco_completo = ''.join(preco_inteiro + centavos)
    print(preco_completo)

else:
    print(f"Erro ao acessar a página: Status Code {response.status_code}")
