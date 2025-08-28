import requests
import time
from scanner.services import utils
from trades.views import _get_exchange_rate

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.1 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://buff.163.com/",
    "Origin": "https://buff.163.com"
}

cookie_str = "Device-Id=28CBbwnyKELAN2J6UbTx; Locale-Supported=en; game=csgo; session=1-kyXFZC70bdEZgqe7QuuZtVIOv2Bs-7DMTNTEi0Y5a-M12036662111; csrf_token=ImQ0ZDc1YmM2MzczMmFjMTZjMjA3MmYyODM2YjI1YjQyZmQ5NzFjMDQi.aIuwrQ.humrQaT8-MJCassXfoi6-2l9NxI"
cookies = {c.strip().split("=", 1)[0]: c.strip().split("=", 1)[1] for c in cookie_str.split(";")}

def get_skin_data(item_id, cnybrl):

    buff_api_url = f"https://buff.163.com/api/market/goods/sell_order?game=csgo&page_num=1&goods_id={item_id}"

    while True:
        try:
            # Send a GET request to the API
            response = requests.get(buff_api_url, headers=headers)#, cookies=cookies)
            response.raise_for_status()  # Raise an exception for bad responses (non-2xx status codes)

            # Parse the JSON response
            data = response.json()

            # Extract the "items" list
            items_list = data.get("data", {}).get("items", [])

            if items_list:
                # If the list is not empty, extract the "price" value from the first item
                buff_price = items_list[0].get("price")
                buff_price = float(buff_price) * float(cnybrl)
                buff_offers = data.get("data", {}).get("total_count", 0)
                break  # Exit the loop if successful
            else:
                #print(f"'{product_name}' price information not found in the response")
                buff_price = 0
                buff_offers = 0
                break

        except requests.RequestException as e:
            None
            #warning(f"An error occurred: {str(e)}\n{product_name} fetch failed...")

        # Sleep before retrying
        time.sleep(0.5)

    buff_price = round(buff_price, 2)

    return {'price': buff_price, 'offers': buff_offers, 'source': 'buff', 'link': buff_api_url}

def get_item_info(item):

    cleared_name = utils.clear_item_name(item)

    cnybrl = _get_exchange_rate("CNY")

    id_dict = utils.load_id_dict()
    item_id = id_dict.get(cleared_name)

    if item_id:
        return get_skin_data(item_id, cnybrl)

    return None