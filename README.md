# S12T2 - Advanced Chatbot Automation

Un sistem complex de automatizare bazat pe Playwright si Discord pentru gestionarea inteligenta a conversatiilor de Facebook Messenger si Instagram Direct. Botul foloseste API-ul Cohere pentru a genera raspunsuri contextuale prin intermediul unor personalitati AI customizabile si simuleaza comportamentul uman pentru a evita detectarea.

## Functionalitati Principale

* Suport Multi-Platforma: Automatizeaza conversatiile atat pe Facebook, cat si pe Instagram.
* Orchestrare prin Discord: Controleaza intregul sistem direct din Discord prin comenzi tip Slash (/) si preia tintele (ID-urile) din canale dedicate.
* Comportament Uman Simulat (Anti-Bot):
  * Include delay-uri realiste de citire si scriere (tastare litera cu litera).
  * Simuleaza miscari naturale ale mouse-ului si scroll.
  * Respecta un program zilnic (ex: nu raspunde noaptea, raspunde mai greu dimineata, este foarte activ seara).
* Memorie si Profilare (SQLite): Botul extrage automat informatii despre persoana cu care vorbeste (nume, varsta, job, status relational, stare emotionala) si le salveaza intr-o baza de date locala (profiles.db). Aceste informatii sunt refolosite pentru a oferi raspunsuri cu un context personalizat.
* Sesiuni Persistente: Salveaza starea browserului (session_fb.json, session_ig.json) pentru a evita logarile repetate si a ocoli alertele de securitate.
* Personalitati AI: Raspunsurile sunt generate pe baza unor prompturi de sistem care definesc "personalitatea" botului (ex: prietena afectuoasa, coleg de munca, vorbitor de engleza stalcita).

## Structura Proiectului

```
chatbot-automation/
├── main.py            # Entry point-ul aplicatiei; gestioneaza inchiderea gratioasa
├── bot.py             # Logica de Discord (evenimente, comenzi slash, sistem de demo)
├── runner.py          # Orchestrarea fluxului (verificare program -> citire -> cohere -> trimitere)
├── browser.py         # Automatizarea Playwright (login, bypass cookie-uri/popup-uri, interactiune DOM)
├── cohere_client.py   # Integrarea cu API-ul Cohere (generare mesaje si extragere date profil)
├── profile_db.py      # Gestionarea bazei de date SQLite (memoria botului)
├── activity.py        # Logica pentru simularea programului uman si a delay-urilor
├── personalities.py   # Dictionarul cu personalitatile AI disponibile
├── config.py          # Incarcarea variabilelor de mediu din .env
├── requirements.txt   # Dependentele proiectului
└── .env.example       # Exemplu de configurare
```

## Instalare si Configurare

1. Instaleaza dependentele:
```bash
pip install -r requirements.txt
```

2. Instaleaza browserele pentru Playwright:
```bash
playwright install chromium
```

3. Configureaza variabilele de mediu:
```bash
cp .env.example .env
```
Asigura-te ca ai completat token-ul Discord, cheia API Cohere si credentialele pentru FB/IG.

## Rulare

```bash
python main.py
```

## Configurare Discord

### 1. Canale Necesare

Botul citeste ID-urile conturilor tinta din canale specifice. Trebuie sa ai urmatoarele canale in serverul tau de Discord (numele pot fi modificate din .env):

* `facebook-ids` - Pentru tintele de Facebook Messenger.
* `instagram-ids` - Pentru tintele de Instagram Direct.

### 2. Formatul Tintelor in Canale

Adauga un ID pe linie, urmat optional de personalitatea dorita, separate prin `|`. Liniile care incep cu `#` sunt ignorate.

```
987654321 | amic
123456789 | iubita
111222333 | englez_stalcit
444555666              # Foloseste personalitatea default (iubita)
```

## Comenzi Discord Disponibile

| Comanda | Descriere |
|---|---|
| `/run` | Porneste fluxul normal de procesare pentru toate ID-urile din canale. Respecta programul uman. |
| `/alwaysonline` | Porneste botul ignorand programul de somn/activitate. Va raspunde in sub 1 minut. |
| `/test <platform> <id> [personalitate]` | Ruleaza botul strict pentru un singur cont. Util pentru debugging. |
| `/personalitati` | Afiseaza o lista cu toate personalitatile definite in cod. |
| `/demo [personalitate]` | Porneste o sesiune de test direct in DM cu botul pe Discord. |
| `/stoptdemo` | Opreste sesiunea activa de demo din DM. |

## Adaugare Personalitate Noua

Editeaza `personalities.py` si adauga o intrare noua in dictionarul `PERSONALITIES`:

```python
"antrenor": {
    "name": "Antrenor de Fitness",
    "prompt": "Esti un antrenor de fitness foarte motivat. Folosesti expresii precum 'Hai trage!', 'Fara scuze!'. Raspunzi la mesaje scurt si la obiect, punand accent pe disciplina."
}
```

## Disclaimer

Acest proiect este realizat exclusiv in scop de educatie si divertisment. Automatizarea conturilor de utilizator pe platforme precum Facebook si Instagram poate incalca Termenii si Conditiile (ToS) ale acestora si poate duce la restrictionarea sau suspendarea conturilor. Nu trebuie luat in serios si nu trebuie sa inlocuiasca interactiunile umane autentice.
