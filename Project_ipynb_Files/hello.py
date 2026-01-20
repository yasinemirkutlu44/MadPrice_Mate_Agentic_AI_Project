import modal
from modal import Image

app_instance = modal.App("hello_instance")
image_instance = Image.debian_slim().pip_install("requests")

# To run locally
@app_instance.function(image=image_instance)
def hello_instance() -> str:
    import requests

    response = requests.get("https://ipinfo.io/json")
    data = response.json()
    city, region, country = data["city"], data["region"], data["country"]
    return f"Hello from {city}, {region}, {country}!"

# To run in the cloud
@app_instance.function(image=image_instance, timeout=60)
def hi_instance_cloud() -> str:
    import requests

    response = requests.get("https://ipinfo.io/json")
    data = response.json()
    city, region, country = data["city"], data["region"], data["country"]
    return f"Hi from {city}, {region}, {country}!"