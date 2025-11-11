import requests
import time
import sys

# Change the encoding to UTF-8 because of the special characters in the skin names
sys.stdout.reconfigure(encoding='utf-8')

remove = [
    "Souvenir",
    "Sticker",
    "PP-Bizon",
    "P-90",
    "MAG-7",
    "XM1014",
    "Negev",
    "M249"
]

def get_items(products, min, max, limit=10000):

    brskins_url = f"https://brskins.gg/api/marketdata/get-market-offers?price_from={min}&price_to={max}&order_by=BestDiscount&pageIndex={'{}'}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.1 Safari/537.36",}
    response = requests.get(brskins_url.format(0), headers = headers)

    if response.status_code != 200:
        erro+=1
        print(f"Erro na requisição para brskins: {response.status_code}")
        print(f"Erro: {response.text}")
        return products

    data = response.json()

    item_counter = 0
    erro = 0
    for page in range(0, 4): # Max 500 items (100 items per page)
        
        if item_counter > limit:
            break
        
        retry = 0
        while retry <= 3:
            try:
                data = requests.get(brskins_url.format(page), headers=headers).json()
                break
            except:
                data = {}
                retry+=1
                time.sleep(2)
        if erro > 5:
            print(f"Too many errors ({erro})... Exiting")
            return products
        elif not data:
            erro += 1
            print(f"Error on page {page}")
            continue

        for item in data['offers']:
            if item_counter > limit:
                break

            product = item['product']
            market_hash_name = product['productCode']
            id = item['id']
            link = f"https://brskins.gg/market/item/{id}"
            price = float(item.get('price', 1e05))

            if any(substring in market_hash_name for substring in remove):
                continue

            if market_hash_name in products and price >= products[market_hash_name].get('price', 0):
                continue

            products[market_hash_name] = {'price': price, 'source': 'brskins', 'link': link}
            item_counter += 1

    print(f"* BR Skins parse concluded. {item_counter} item's analyzed")
    return products

if __name__ == "__main__":
    products = {}
    products = get_items(products, 20, 350, 150)
    for name, info in products.items():
        print(f"{name}: {info}")