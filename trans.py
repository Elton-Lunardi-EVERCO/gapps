import threading
import time
import os
from bs4 import BeautifulSoup
from translate import Translator
import re


def traduzir_texto(texto, lang_from="en", lang_to="pt"):
    # Usar expressões regulares para encontrar o texto entre chaves e blocos {% %}
    partes_nao_traduzir = re.findall(r"(\{.*?\}|\{%.*?%\})", texto)
    partes_traduzir = re.split(r"(\{.*?\}|\{%.*?%\})", texto)

    translator = Translator(from_lang=lang_from, to_lang=lang_to)

    # Traduzir apenas as partes que não estão entre chaves ou blocos {% %}
    texto_traduzido = ""
    for parte in partes_traduzir:
        if parte in partes_nao_traduzir:
            texto_traduzido += parte
        else:
            texto_traduzido += translator.translate(parte)

    return texto_traduzido


def traduzir_html(file_path, output_paths, lang_from="en", lang_to="pt"):
    with open(file_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Tags que queremos traduzir
    tags_para_traduzir = [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "span",
        "a",
        "div",
        "label",
        "li",
        "ul",
        "th",
        "tr",
        "option",
    ]

    for tag in tags_para_traduzir:
        for element in soup.find_all(tag):
            if element.string:  # Verifica se o elemento tem um texto simples
                element.string.replace_with(
                    traduzir_texto(element.string, lang_from, lang_to)
                )
            elif element.contents:  # Verifica se o elemento tem conteúdo
                for i, content in enumerate(element.contents):
                    if isinstance(content, str):
                        element.contents[i].replace_with(
                            traduzir_texto(content, lang_from, lang_to)
                        )

    for output_path in output_paths:
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        output_file_path = os.path.join(output_path, os.path.basename(file_path))
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(str(soup))


def traduzir_pasta(folder_path, output_paths, lang_from="en", lang_to="pt"):
    for filename in os.listdir(folder_path):
        if filename.endswith(".html"):
            file_path = os.path.join(folder_path, filename)
            traduzir_html(file_path, output_paths, lang_from, lang_to)


def mostrar_loading():
    while not traducao_concluida:
        for frame in ["|", "/", "-", "\\"]:
            print(f"\rLoading {frame}", end="")
            time.sleep(0.1)


# Variável global para controle do carregamento
traducao_concluida = False

# Caminho da pasta com arquivos HTML
folder_path = "app/templates/"

# Caminhos das pastas de saída
output_paths = ["app/output/"]

# Cria e inicia o thread para a tradução
thread_traducao = threading.Thread(
    target=traduzir_pasta, args=(folder_path, output_paths)
)
thread_loading = threading.Thread(target=mostrar_loading)

thread_traducao.start()
thread_loading.start()

# Aguarda o fim da tradução
thread_traducao.join()
traducao_concluida = True
thread_loading.join()

print("\nTradução concluída!")
