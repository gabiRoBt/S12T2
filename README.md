# S12T2

Discord bot + Playwright automation pentru gestionarea conversatiilor de Facebook si Instagram cu personalitati AI prin Cohere.

## Structura

```
chatbot-automation/
├── main.py            # Entry point
├── bot.py             # Discord bot + slash commands
├── runner.py          # Orchestrare conturi
├── browser.py         # Playwright (FB + IG)
├── cohere_client.py   # API Cohere
├── personalities.py   # Personalitati disponibile
├── config.py          # Setari din .env
├── requirements.txt
├── .env.example
└── .gitignore
```

## Instalare

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# editeaza .env cu credentialele tale
```

## Rulare

```bash
python main.py
```

## Canale Discord necesare

| Canal | Scop |
|---|---|
| `facebook-ids` | ID-uri conturi Facebook |
| `instagram-ids` | ID-uri conturi Instagram |
| `comenzi` | Unde rulezi comenzile |

## Format ID-uri in canale

```
987654321 | amic
123456789 | iubita
111222333 | englez_stalcit
444555666              # foloseste personalitatea default (amic)
```

## Comenzi Discord

| Comanda | Descriere |
|---|---|
| `/run` | Porneste botul pentru toate conturile |
| `/test platform id personality` | Testeaza un singur cont |
| `/personalitati` | Afiseaza personalitati disponibile |


## Adaugare personalitate noua

In `personalities.py`, adauga un nou bloc in dictionar:

```python
"coleg_de_munca": {
    "name": "Coleg",
    "prompt": "Esti un coleg care..."
}
```

## Disclaimer

Acest proiect este realizat exclusiv in scop de divertisment. Nu trebuie luat in serios si nu trebuie sa inlocuiasca interactiunile umane.