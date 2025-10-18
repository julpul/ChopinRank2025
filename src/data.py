from pathlib import Path
import os
import pandas as pd

from yt_dlp import YoutubeDL

from pydub import AudioSegment
import json
import unicodedata
import re




FORBIDDEN = r'[\\/:*?"<>|]'

XVIII_Competition_Firs_stage = "https://www.youtube.com/playlist?list=PLTmn2qD3aSQu5qSHkFIezKnkCMWekntk3"
XVIII_Competition_Second_stage = "https://www.youtube.com/playlist?list=PLTmn2qD3aSQtUl-oPRcgm3kGiGjWkLJzN"
XVIII_Competition_Third_stage = "https://www.youtube.com/playlist?list=PLTmn2qD3aSQtn2fE4OC_LTx6podD7JYXU"
RESULTS = {}


def norm_key(s: str) -> str:
    if s is None:
        return ""
    s = s.strip()
    s_basic = s.casefold()
    return s_basic

def norm_key_no_diacritics(s: str) -> str:
    if s is None:
        return ""
    s = s.strip().casefold()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s)
    return s


def get_qualified_stage(stage):
    if "first round" == stage:
        return "second round"
    elif "second round" == stage:
        return "third round"
    elif "third round" == stage:
        return "final"


def extact_metadata_from_recital(url):
    pianistMap = {}
    with YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        print(info["title"])

        title = info.get("title", "")
        m = re.match(
            r"^(?P<name>.+?)\s*[–—-]\s*(?P<stage>first round|second round|third round|final)\s*\((?P<competition>\d{2}th Chopin Competition)",
            title, flags=re.I)
        name = m["name"].strip()
        stage = m["stage"].strip().lower()
        competition = m["competition"].strip()

        date = re.split(r"\n", info['description'], maxsplit=1)[0].strip()
        nationality = re.search(r"\(([^/]+)\s*/\s*([^)]+)\)", info['description']).group(2).strip()
        pianistMap["name"] = name
        pianistMap["date"] = date
        pianistMap['competition'] = competition
        pianistMap['stage'] = stage
        pianistMap['nationality'] = nationality
        pianistMap['piano'] = re.search(r"piano:\s*(.+)", info['description']).group(1).strip()
        pianistMap['url'] = url

        next_stage = get_qualified_stage(stage)
        lista = RESULTS[competition][next_stage]['qualified']

        index_by_pianist = {norm_key(q["pianist"]): q for q in lista}


        if norm_key(name) in index_by_pianist:
            pianistMap["qualified"] = True
        else:
            pianistMap["qualified"] = False


        if "chapters" in info:
            pieces = []
            for c in info["chapters"]:
                if c['title'] != '<Untitled Chapter 1>':
                    pieces.append(
                        {"title_pl": c['title'].split("/")[0].strip(), "title_en": c['title'].split("/")[1].strip(),
                         'start': c['start_time'], 'end': c['end_time']})
            pianistMap['pieces'] = pieces
    return pianistMap


def sanitize(name: str) -> str:
    # wytnij znaki niedozwolone i nadmiarowe spacje
    return re.sub(FORBIDDEN, "_", name).strip()


def cut_recital_by_pieces(base_path, path_recital, metadata):
    base = Path(base_path)
    pieces_dir = base / "pieces"
    meta_dir = base / "metadata"
    pieces_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    # wczytaj raz
    audio = AudioSegment.from_file(path_recital)

    for piece in metadata.get('pieces', []):
        start_ms = int(piece['start'] * 1000)
        end_ms = int(piece['end'] * 1000)

        fname = f"{metadata['name']}-{metadata['date']}-{metadata['competition']}-{metadata['stage']}-{piece['title_en']}.wav"
        out_path = pieces_dir / sanitize(fname)
        fragment = audio[start_ms:end_ms]
        fragment.export(out_path, format="wav")

    # sprzątnij plik całościowy
    try:
        Path(path_recital).unlink(missing_ok=True)
    except Exception:
        pass

    # metadata
    with (meta_dir / "data.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(
        "+-download recital " + f"{metadata['name']}-{metadata['date']}-{metadata['competition']}-{metadata['stage']}\n")

def download_wav(url):
    metadata = extact_metadata_from_recital(url)
    folder_path = os.path.join("../Data", 'raw', metadata['competition'], metadata['stage'], metadata['name'])
    Path(folder_path).mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        'ffmpeg_location': r'C:\ffmpeg-7.1.1-essentials_build\bin',
        'format': 'bestaudio[acodec^=opus]/bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best',
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav', 'preferredquality': '0'}
        ],
        'outtmpl': os.path.join(folder_path, '%(title)s.%(ext)s'),
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    cut_recital_by_pieces(folder_path, os.path.join(folder_path, info['title'] + '.wav'), metadata)

def process_playlist_individually(playlist_url):
    print("download playlist "+playlist_url)
    ydl_opts = {"extract_flat": True, "skip_download": True}
    with YoutubeDL(ydl_opts) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)
        entries = playlist_dict.get("entries", [])
        error_logs = {}
        errors=[]
        error_logs['errors'] = errors


        for i, entry in enumerate(entries):
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            print(f"\n▶️ [{i+1}/{len(entries)}] Przetwarzam: {entry['title']}")
            try:
                download_wav(video_url)
            except Exception as e:
                print(f"❌ Błąd przy {video_url}: {e}")
                errors.append({"url":video_url,"message":str(e)})

        #error logs
        log_file_path = Path() / "logs" / "download.json"
        log_file_path.mkdir(parents=True, exist_ok=True)

        with log_file_path.open("w", encoding="utf-8") as f:
            json.dump(error_logs, f, ensure_ascii=False, indent=2)


def separate_resoults():
    results = {}

    for dirpath, _, filenames in os.walk("..\\Data\\resoults"):
        stage = dirpath.split("\\")[-1]
        competition = dirpath.split("\\")[-2]

        for filename in filenames:
            if filename.endswith(".csv"):
                filepath = os.path.join(dirpath, filename)
                file_csv = pd.read_csv(filepath)

                qualified = [
                    {"pianist": pianist, "country": country}
                    for pianist, country in file_csv[["Pianist", "country"]].itertuples(index=False, name=None)
                ]

                # zagnieżdżony słownik
                results.setdefault(competition, {})[stage] = {"qualified": qualified}

    return results

def test(resoults):
    lista = resoults['19th Chopin Competition']['first round']['qualified']
    index_by_pianist = {q["pianist"]: q for q in lista}

    name = "Piotr Alexewicz"
    if name in index_by_pianist:
        print(index_by_pianist[name])

def main():
    global RESULTS;
    RESULTS = separate_resoults()
    #print(RESULTS)
    process_playlist_individually(XVIII_Competition_Firs_stage)


if __name__ == '__main__':
    main()