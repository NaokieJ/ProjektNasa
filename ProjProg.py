import requests
import json
from tkinter import *
from tkinter.ttk import *
import io
from PIL import ImageTk, Image
import pygame
import asyncio
import aiohttp
import sqlite3
import os




# Pobieranie z API
def PobrZdjNasa(query):
    url = "https://images-api.nasa.gov/search"
    params_q = {'q': query}
    response = requests.get(url, params=params_q)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Nie udało się pobrać danych, kod błędu: {response.status_code}')


# Zamiana obrazu PIL na Pygame
def PilNaPygame(pil_image):
    mode = pil_image.mode
    size = pil_image.size
    data = pil_image.tobytes()
    return pygame.image.fromstring(data, size, mode)


# Asynchroniczne pobieranie obrazu
async def pobierzObraz(url):
    try:
        async with aiohttp.ClientSession() as session:
            #User-agents, żeby symulować zapytanie przeglądarki, inaczej blokuje mi dostęp
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    image_data = await response.read()
                    pil_image = Image.open(io.BytesIO(image_data)).convert("RGB")
                    return pil_image
                else:
                    print(f"Błąd podczas pobierania obrazu: HTTP {response.status}")
                    return None
    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania obrazu: {e}")
        return None



# pygame do wyświetlania
def podgladPygame(images):
    pygame.init()
    screen = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Zdjęcia NASA")

    #tło
    BLACK = (0, 0, 0)

    selected_image = None
    running = True

    while running:
        screen.fill(BLACK)

        # Powiększanie zdjęcia
        if selected_image:
            screen.blit(pygame.transform.scale(selected_image['full'], screen.get_size()), (0, 0))
        else:
            #wyświetlanie miniatur
            for i, img in enumerate(images):
                x = 220 * i + 20
                y = 200
                screen.blit(img['thumbnail'], (x, y))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Esc
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    selected_image = None

            # Powiększenie zdjęcia
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not selected_image:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    for i, img in enumerate(images):
                        x = 220 * i + 20
                        y = 200
                        if x <= mouse_x <= x + 200 and y <= mouse_y <= y + 200:
                            selected_image = img
                            break

    pygame.quit()

# Baza danych
def InicjalizujBaze():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "nasa.db")
    conn = sqlite3.connect(db_path)

    cursor = conn.cursor()

    # Tabela wyszukiwan
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wyszukiwania (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zapytanie TEXT UNIQUE,
            czas TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela obrazów
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS obrazy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_wyszukiwania INTEGER,
            tytul TEXT,
            url TEXT,
            FOREIGN KEY(id_wyszukiwania) REFERENCES wyszukiwania(id)
        )
    ''')

    conn.commit()
    conn.close()


# Sprawdzenie czy istnieje w bazie
def SprawdzWBazie(zapytanie):
    conn = sqlite3.connect("nasa.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM wyszukiwania WHERE zapytanie = ?", (zapytanie,))
    wynik = cursor.fetchone()
    conn.close()
    return wynik


# Zapisanie do bazy
def ZapiszDoBazy(zapytanie, obrazy):
    conn = sqlite3.connect("nasa.db")
    cursor = conn.cursor()

    cursor.execute("INSERT OR IGNORE INTO wyszukiwania (zapytanie) VALUES (?)", (zapytanie,))
    conn.commit()

    cursor.execute("SELECT id FROM wyszukiwania WHERE zapytanie = ?", (zapytanie,))
    wynik = cursor.fetchone()
    if not wynik:
        conn.close()
        return
    id_wyszukiwania = wynik[0]

    for obraz in obrazy:
        cursor.execute('''
            INSERT INTO obrazy (id_wyszukiwania, tytul, url)
            VALUES (?, ?, ?)
        ''', (id_wyszukiwania, obraz['tytul'], obraz['url']))

    conn.commit()
    conn.close()


# Pobranie z bazy
def PobierzZBazy(zapytanie):
    conn = sqlite3.connect("nasa.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM wyszukiwania WHERE zapytanie = ?", (zapytanie,))
    wynik = cursor.fetchone()
    if not wynik:
        conn.close()
        return []

    id_wyszukiwania = wynik[0]
    cursor.execute("SELECT tytul, url FROM obrazy WHERE id_wyszukiwania = ?", (id_wyszukiwania,))
    rekordy = cursor.fetchall()
    conn.close()

    return [{'tytul': t, 'url': u} for t, u in rekordy]



# Główna aplikacja
class App(Frame):
    window = 0

    def __init__(self):
        InicjalizujBaze()  # Inicjalizacja bazy

        # Główne okno aplikacji
        self.window = Tk()

        # Pole do wpisania nazwy
        label = Label(text="Wpisz nazwę")
        label.pack()

        TekstPopUp = Entry()
        TekstPopUp.pack()

        button = Button(self.window, text="Wyszukaj", command=lambda: self.Search(TekstPopUp.get()))
        button.pack()

        # Główna pętla
        self.window.mainloop()

    # Wyszukiwanie zdjęć
    def Search(self, query):
        Obrazy = Toplevel(self.window)

        try:
            # Sprawdzenie czy wynik już jest w bazie
            dane_z_bazy = PobierzZBazy(query)
            if dane_z_bazy:
                print("Wyniki z bazy danych:")
                images = []

                async def fetch_from_db():
                    for item in dane_z_bazy:
                        print(f"Tytuł: {item['tytul']}")
                        pil_image = await pobierzObraz(item["url"])
                        if pil_image:
                            thumbnail = pil_image.resize((200, 200))
                            images.append({
                                'thumbnail': PilNaPygame(thumbnail),
                                'full': PilNaPygame(pil_image),
                                'title': item["tytul"]
                            })
                    podgladPygame(images)

                asyncio.run(fetch_from_db())
                return

            # Pobieranie z API do wyświetlania
            data = PobrZdjNasa(query)
            items = data.get('collection', {}).get('items', [])

            if not items:
                print("Brak wyników wyszukiwania")
                return

            images = []  # Przechowywanie obrazów
            lista_do_bazy = []  # Do zapisu w bazie

            # Pobieranie obrazów asynch
            async def fetch_images_async():
                for item in items[:5]:
                    item_data = item.get("data", [])
                    if item_data:
                        # Pobieranie tytułów
                        title = item_data[0].get("title", "Brak tytułu")
                        print(f'Tytuł: {title}')

                    # Linki obrazów
                    links = item.get('links', [])
                    if links:
                        href = links[0].get('href', None)
                        if href:
                            try:
                                pil_image = await pobierzObraz(href)
                                if pil_image:
                                    thumbnail = pil_image.resize((200, 200))  # Miniatura
                                    images.append({
                                        'thumbnail': PilNaPygame(thumbnail),
                                        'full': PilNaPygame(pil_image),
                                        'title': title
                                    })

                                    # Dodawanie do listy do bazy
                                    lista_do_bazy.append({
                                        'tytul': title,
                                        'url': href
                                    })
                            except Exception as img_error:
                                print(f"Wystąpił błąd podczas przetwarzania obrazu: {img_error}")

                # Zapisz do bazy po pobraniu
                ZapiszDoBazy(query, lista_do_bazy)

                # Uruchomienie pygame
                podgladPygame(images)

            # Uruchomienie asynch
            asyncio.run(fetch_images_async())

        except Exception as e:
            print(f"Wystąpił błąd: {e}")


# Tkinter
def main():
    a = App()


if __name__ == "__main__":
    main()
