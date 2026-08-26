import requests

TOKEN = "8828118024:AAEUqSOABc2U5QJidjdrmlbvFFqodE-Broc"
CHAT_ID = "-5587626942"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "Halo, ini pesan test dari bot NorthrenTicketBot!"
}

response = requests.post(url, data=payload)
print(response.json())