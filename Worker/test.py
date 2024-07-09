import subprocess

def download_and_convert_m3u8_to_mp3(m3u8_url, output_filename):
    command = [
        'ffmpeg',
        '-i', m3u8_url,
        '-c:a', 'libmp3lame',
        '-q:a', '320',
        output_filename
    ]

    subprocess.run(command)

download_and_convert_m3u8_to_mp3('https://cs9-5v4.vkuseraudio.net/s/v1/ac/LBG49IfjR3MSEcQwQPIAue4oiFylKaNKEi2rbTUUeetREgvTlVTOWNEFwhDSrDMah0M_PctpULqwxEVLf8jodbLPQYHiufvM-23FAZqmYMvsEITSO8m0m-TXXlmlnGHF7HHCS3RDFbPPIV31wYjcSpyMYGfyHXTSoiKTBKoxF4sFqLk/index.m3u8?siren=1', 'track.mp3')