import yt_dlp

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': False,          # Para ver logs
    'no_warnings': False,
    'ignoreerrors': True,
    'nocheckcertificate': True,
    'cookiefile': 'cookies.txt'  # seu arquivo de cookies existente
}

url = "https://www.youtube.com/watch?v=fPqH9FHfdiw"

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    print(info['title'])
    if 'url' in info:
        print("URL do áudio:", info['url'])