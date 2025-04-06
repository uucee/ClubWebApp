from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    secret_key = get_random_secret_key()
    print(f"Generated Secret Key: {secret_key}")
    print("\nCopy this key and use it in your azure-settings.json file") 