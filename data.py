import os

from yt_dlp import YoutubeDL
import re
import pandas as pd

from yt_dlp.compat import compat_expanduser

url = "https://www.youtube.com/watch?v=C9DnR1saRXs"
ydl_opts = {
    "format": "bestaudio/best",         # wybierz najlepszy dostępny dźwięk
    "outtmpl": "music_data/%(title)s.%(ext)s",     # nazwa pliku = tytuł
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "wav",     # <-- zamiast mp3
        "preferredquality": "0",     # bezstratna jakość (dla WAV bez znaczenia)
    }],
    "writeinfojson": True,
    "writedescription": True,
}



def extact_metadata(url):
    pianistMap = {}
    with YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)

        title = info.get("title", "")
        name = re.split(r"\s*[–—-]\s*", title, maxsplit=1)[0].strip()
        competition = re.search(r"\(([^,]+),", title).group(1).strip()
        date = re.split(r"\n", info['description'], maxsplit=1)[0].strip()
        stage = re.search(r"[–—-]([^,]+)\(", title).group(1).strip()
        nationality = re.search(r"\(([^/]+)\s*/\s*([^)]+)\)", info['description']).group(2).strip()

        pianistMap["name"] = name
        pianistMap["date"] = date
        pianistMap['competition'] = competition
        pianistMap['stage'] = stage
        pianistMap['nationality'] = nationality
        pianistMap['piano'] = re.search(r"piano:\s*(.+)", info['description']).group(1).strip()

        if "chapters" in info:
            pieces = []
            for c in info["chapters"]:
                if c['title'] != '<Untitled Chapter 1>':
                    pieces.append(
                        {"title_pl": c['title'].split("/")[0].strip(), "title_en": c['title'].split("/")[1].strip(),
                         'start': c['start_time'], 'end': c['end_time']})
            pianistMap['pieces'] = pieces
    return pianistMap


def cut_recital_by_plan(path,pieces):
    for piece in pieces:
        piece_title = piece['title_en']






def download_wav(url):
    metadata = extact_metadata(url)
    folder_path = os.path.join("DaTA", metadata['competition'], metadata['stage'], metadata['name'])

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(folder_path, "%(title)s.%(ext)s"),  # plik całości (przyda się jako fallback)
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            },
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    cut_recital_by_plan(os.path.join(folder_path,info['title'],'wav'),metadata['pieces'])



download_wav(url)