import asyncio
import httpx
from bs4 import BeautifulSoup
import json
import logging
from google_sheet import upload_data_to_sheet
from requestmask import get_random_headers, build_url

# Config
MAX_PROPERTIES_PER_PAGE = 20
MAX_PAGES = 100
CONCURRENT_REQUESTS = 3
REQUEST_DELAY = 0  # seconds

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def fetch_properties(query, page, client, semaphore):
    """Asynchronously fetch property data with concurrency control."""
    url = (
        f"https://www.propertyfinder.{query['country']}/en/search"
        f"?l={query['location']}&c={query['category']}&fu={query['furnishing']}"
        f"&rp={query['rental_period']}&ob={query['sort_by']}&page={page}"
    )
    target_url = build_url(url)

    headers = get_random_headers()

    async with semaphore:
        try:
            logging.info(f"Fetching page {page}")
            response = await client.get(target_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            script_tag = soup.find("script", id="__NEXT_DATA__")
            if not script_tag or not script_tag.string:
                logging.warning(f"No data found on page {page}")
                return None
            return script_tag.string
        except httpx.HTTPError as e:
            logging.error(f"HTTP error on page {page}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error on page {page}: {e}")
        return None


def extract_property_data(json_data):
    """Extract structured property data from JSON string."""
    if not json_data:
        return []

    try:
        data = json.loads(json_data)
        properties = data['props']['pageProps']['searchResult']['properties']
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"JSON parsing error: {e}")
        return []

    property_list = []
    for prop in properties:
        try:
            data = {
                "ID": prop.get("id"),
                "Title": prop.get("title"),
                "Property Type": prop.get("property_type"),
                "Price": f"{prop['price']['value']} {prop['price']['currency']} / {prop['price']['period']}",
                "Bedrooms": prop.get("bedrooms"),
                "Bathrooms": prop.get("bathrooms"),
                "Size": f"{prop['size']['value']} {prop['size']['unit']}" if prop.get("size") else None,
                "Furnished": prop.get("furnished"),
                "Listed Date": prop.get("listed_date"),
                "RERA ID": prop.get("rera"),
                "Location": prop.get("location", {}).get("full_name"),
                "Map Link": (
                    f"https://www.google.com/maps?q="
                    f"{prop.get('location', {}).get('coordinates', {}).get('lat')},"
                    f"{prop.get('location', {}).get('coordinates', {}).get('lon')}"
                ),
                "Listing URL": prop.get("share_url"),
                "Image URL": prop.get("images", [{}])[0].get("medium"),
                "Agent Name": prop.get("agent", {}).get("name"),
                "Agent Email": prop.get("agent", {}).get("email"),
                "Super Agent": prop.get("agent", {}).get("is_super_agent"),
                "Broker Name": prop.get("broker", {}).get("name"),
                "Broker Email": prop.get("broker", {}).get("email"),
                "Broker Phone": prop.get("broker", {}).get("phone"),
                # "Description": (prop.get("description") or "")[:150] + ("..." if prop.get("description") else ""),
                "Description": (lambda d: (', '.join(line.strip('- ').strip() for line in (d or '').splitlines())).strip()[:150] + ('...' if d and len(d) > 150 else ''))(prop.get("description"))
            }
            property_list.append(data)
        except Exception as e:
            logging.warning(f"Failed to extract property data: {e}")
    return property_list


def input_query_parameters():
    """Interactive CLI input for search query parameters with validation."""
    Countries = {
        "ae": "United Arab Emirates",
        "qa": "Qatar",
        "bh": "Bahrain",
        "eg": "Egypt",
        "sa": "Saudi Arabia"
    }
    Locations = {
        "ae": {1: "Dubai", 6: "Abu Dhabi", 4: "Sharjah", 5: "Ajman", 3: "Ras Al Khaimah", 8: "Al Ain", 7: "Fujairah", 2: "Umm Al Quwain"},
        "qa": {9: "Doha", 4: "Lusail", 2: "Al Wakra", 5: "Umm Salal Mohammad", 6: "Al Shamal", 3: "Al Khor", 7: "Al Daayen"},
        "bh": {34: "Manama", 49: "Riffa", 12: "Muharraq", 00: "Isa Town", 00: "Hamad Town", 00: "Sitra", 00: "Jidhafs"},
        "eg": {2254: "Cairo", 20663: "Giza", 30754: "Alexandria", 00: "Mansoura", 00: "Tanta", 00: "Asyut", 00: "Ismailia"},
        "sa": {8216: "Riyadh", 2658: "Jeddah", 00: "Mecca", 00: "Medina", 00: "Dammam", 00: "Khobar", 00: "Dhahran"}
    }
    Categories = {1: "buy", 2: "rent", 3: "commercial-buy", 4: "commercial-rent", 5: "new-projects"}
    Furnishing = {0: "All furnishings", 1: "Furnished", 2: "Unfurnished", 3: "Partly furnished"}
    RentalPeriods = {"y": "yearly", "m": "monthly", "w": "weekly", "d": "daily"}
    SortByOptions = {"mr": "Featured", "nd": "Newest", "pa": "Price (low)", "pd": "Price (high)", "ba": "Beds (least)", "bd": "Beds (most)"}

    def get_choice(prompt, options, default=None, key_type=str):
        while True:
            print(prompt)
            for k, v in options.items():
                print(f"{k}: {v}")
            choice = input("Your choice: ").strip()
            try:
                choice_casted = key_type(choice)
                if choice_casted in options:
                    return choice_casted
            except Exception:
                pass
            if default is not None:
                print(f"Invalid input, defaulting to {default} ({options[default]})")
                return default
            print("Invalid input, please try again.\n")

    print("=== Property Search Query Parameters ===")
    country = get_choice("Select a country code:", Countries, default='ae')
    query = {'country': country}

    locations = Locations.get(country, Locations['ae'])
    location_id = get_choice("Select a location value:", locations, default=list(locations.keys())[0], key_type=int)
    query['location'] = location_id

    category_id = get_choice("Select a category ID:", Categories, default=1, key_type=int)
    query['category'] = category_id

    furnishing_id = get_choice("Select a furnishing option ID:", Furnishing, default=0, key_type=int)
    query['furnishing'] = furnishing_id

    rental_period = get_choice("Select a rental period code:", RentalPeriods, default='y')
    query['rental_period'] = rental_period

    sort_by = get_choice("Select a sort by code:", SortByOptions, default='mr')
    query['sort_by'] = sort_by

    return query


async def main():
    query = input_query_parameters()
    all_properties = []
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async with httpx.AsyncClient() as client:
        tasks = []
        for page in range(1, MAX_PAGES + 1):
            tasks.append(fetch_properties(query, page, client, semaphore))

        results = await asyncio.gather(*tasks)

        for page, json_data in enumerate(results, start=1):
            properties = extract_property_data(json_data)
            if not properties:
                break
            all_properties.extend(properties)
            if len(properties) < MAX_PROPERTIES_PER_PAGE:
                logging.info(f"Last page reached at page {page}.")
                break
            await asyncio.sleep(REQUEST_DELAY)

    logging.info(f"Fetched {len(all_properties)} total properties.")
    if all_properties:
        upload_data_to_sheet(all_properties, query["country"])
        logging.info("Upload to Google Sheet complete.")
    else:
        logging.warning("No properties fetched to upload.")


if __name__ == "__main__":
    asyncio.run(main())
