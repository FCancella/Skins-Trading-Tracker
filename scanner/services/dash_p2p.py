import requests

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
    dash_p2p_url = f"https://api.dashskins.gg/v1/item?pageSize=100000&maxPriceBRL={max}&minPriceBRL={min}&sort=discount-desc"

    response = requests.get(dash_p2p_url)
    data = response.json()

    dash_p2p_items = data.get("page", [])

    item_counter = 0

    if dash_p2p_items:
        for item in dash_p2p_items:
            if item_counter > limit:
                break
            name = item.get("marketHashName")
            price = item.get("priceBRL")

            if any(substring in name for substring in remove):
                continue

            #Check if the item qualifies for the items list
            if name in products and price >= products[name].get('price', 0):
                # Skip this item as it's more expensive than the one already seen
                continue
            
            # Add/Update the item on the dictionary of viewed items
            products[name] = {'price': price, 'source': 'dash_p2p'}
            item_counter += 1

    print(f"* P2P DashSkins parse concluded. {len(dash_p2p_items)} item's analyzed")
    return products