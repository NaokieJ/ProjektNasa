import requests
import json
from tkinter import *
from tkinter.ttk import *
import io
from PIL import ImageTk, Image
import pygame

# Pobieranie z API
def fetch_nasa_images(query):
    # Pobieranie zdjec
    url = "https://images-api.nasa.gov/search"

    params_q = {'q': query}
    response = requests.get(url, params=params_q)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Nie udało się pobrać danych, kod błędu: {response.status_code}')


# Zamiana obrazu PIL na pygame
def PilNaPygame(pil_image):
    mode = pil_image.mode
    size = pil_image.size
    data = pil_image.tobytes()
    return pygame.image.fromstring(data, size, mode)

# Główna aplikacja
class App(Frame):
    window = 0

    def __init__(self):
        #głowne okno aplikacji
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


    # Wyszukiwanie zdjeć
    def Search(self, query):
        Obrazy = Toplevel(self.window)

        try:
            # Pobieranie z API do wyświetlania
            data = fetch_nasa_images(query)
            items = data.get('collection', {}).get('items', [])

            if not items:
                print("Brak wyników wyszukiwania")
                return

            images = [] #Przechowywanie obrazów

            for item in items[:5]:
                item_data = item.get("data", [])


                if item_data:
                    #pobieranie tytułów
                    title = item_data[0].get("title", "Brak tytułu")
                    print(f'Tytuł: {title}')

                # linki obrazów
                links = item.get('links', [])


                if links:
                    href = links[0].get('href', None)
                    if href:
                        try:
                            # Pobieranie obrazu
                            image_bytes = requests.get(href).content
                            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                            thumbnail = pil_image.resize((200, 200))  # Miniatura
                            images.append({
                                'thumbnail': PilNaPygame(thumbnail),
                                'full': PilNaPygame(pil_image),
                                'title': title
                            })

                        except Exception as img_error:
                            print(f"Wystąpił błąd: {img_error}")

            # Uruchamianie pygame
            self.window.withdraw()  #Ukrywa okno Tkinter
            run_pygame_viewer(images, self.window)

        except Exception as e:
            print(f"Wystąpił błąd: {e}")


# Uruchamianie pygame do wyświetlania zdjęć
def run_pygame_viewer(images, show_window):
    pygame.init()
    screen = pygame.display.set_mode((1000, 600))
    pygame.display.set_caption("Zdjęcia NASA")

    #tło
    BLACK = (0, 0, 0)

    selected_image = None
    running = True

    while running:
        screen.fill(BLACK)

        # powiększanie zdjęcia
        if selected_image:
            screen.blit(pygame.transform.scale(selected_image['full'], screen.get_size()), (0, 0))
        else:
            # Wyświetlanie miniatur
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

            #powiększenie zdjęcia
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

    # Zamykanie tkinter
    show_window.deiconify()


#Tkinter
def main():
    a = App()


if __name__ == "__main__":
    main()
