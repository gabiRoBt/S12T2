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
S12T2/
├── main.py                # Entry point-ul aplicatiei; gestioneaza inchiderea gratioasa a botului
├── bot/                   # Logica de Discord (evenimente, comenzi slash, sistem de demo, citire canale)
│   ├── __init__.py        # Initializarea si setarea botului de Discord
│   ├── channel_reader.py  # Functii pentru citirea ID-urilor tinta din canalele de Discord
│   ├── commands.py        # Definirea si inregistrarea comenzilor Slash (/run, /test, /demo etc.)
│   └── demo.py            # Logica pentru gestionarea conversatiilor de test in DM
├── core/                  # Orchestrarea fluxului (verificare program, cohere, update db, runner)
│   ├── __init__.py        # Expunerea functiilor principale din modul
│   ├── activity.py        # Logica pentru simularea programului zilnic si delay-urilor umane
│   ├── cohere_client.py   # Functii pentru interogarea API-ului Cohere (generare raspunsuri si extragere profil)
│   ├── profile_db.py      # Baza de date SQLite pentru memoria/profilul utilizatorilor contactati
│   └── runner.py          # Bucla de orchestrare: citire conversatie -> generare raspuns -> trimitere
├── browser/               # Automatizarea Playwright (login, bypass cookie-uri/popup-uri, interactiune DOM)
│   ├── __init__.py        # Expunerea claselor de browser
│   ├── actions.py         # Functii pentru simularea actiunilor umane (scroll, miscare mouse, typing delay)
│   ├── facebook.py        # Logica specifica de automatizare pentru platforma Facebook Messenger
│   ├── instagram.py       # Logica specifica de automatizare pentru platforma Instagram Direct
│   ├── popups.py          # Functii destinate inchiderii dialogurilor (cookies, conectare, PIN e2ee)
│   └── session.py         # Gestionarea instantelor si contextelor de Chromium (salvare/incarcare sesiune)
├── logger.py              # Sistemul de logging pentru consola si fisiere locale
├── personalities.py       # Dictionarul cu personalitatile AI disponibile (prompturile sistemului)
├── config.py              # Incarcarea variabilelor de mediu din fisierele .env
├── requirements.txt       # Dependentele proiectului (ex: discord.py, playwright, httpx, cohere etc.)
├── .env.example           # Exemplu de configurare a variabilelor de mediu
├── .gitignore             # Specificarea fisierelor ignorate de Git (sesiuni, log-uri, venv)
└── README.md              # Documentatia proiectului cu instructiuni de instalare si folosire
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
Asigura-te ca ai completat token-ul Discord, cheia API Cohere si credentialele pentru conturile de Facebook si Instagram.

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
| `/stopdemo` | Opreste sesiunea activa de demo din DM. |

## Adaugare Personalitate Noua

Editeaza fisierul `personalities.py` si adauga o intrare noua in dictionarul `PERSONALITIES`:

```python
"antrenor": {
    "name": "Antrenor de Fitness",
    "prompt": "Esti un antrenor de fitness foarte motivat. Folosesti expresii precum 'Hai trage!', 'Fara scuze!'. Raspunzi la mesaje scurt si la obiect, punand accent pe disciplina."
}
```

## Disclaimer

Acest proiect este realizat exclusiv in scop de educatie si divertisment. Automatizarea conturilor de utilizator pe platforme precum Facebook si Instagram poate incalca Termenii si Conditiile (ToS) ale acestora si poate duce la restrictionarea sau suspendarea conturilor. Nu trebuie luat in serios si nu trebuie sa inlocuiasca interactiunile umane autentice.