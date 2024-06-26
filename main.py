import jpype
import jpype.imports
from jpype.types import JString
import pandas as pd
import json
from difflib import SequenceMatcher
import time

# Dosya yollarını belirleyelim
file_path_1 = r'C:\Users\lenovo\Desktop\proje\icerik1.xlsx'
file_path_2 = r'C:\Users\lenovo\Desktop\proje\icerik2.xlsx'
output_path = r'C:\Users\lenovo\Desktop\proje\eslestirme.csv'

# Verileri yükleyelim
icerik1 = pd.read_excel(file_path_1)
icerik2 = pd.read_excel(file_path_2)

# İlk 50 satırı alalım
icerik1 = icerik1.head(50)
icerik2 = icerik2.head(50)

# JSON verilerini önbelleğe alalım
def cache_json_data(data):
    # Verilen DataFrame'deki her hücredeki JSON verilerini önbelleğe alır
    cached_data = []
    for index, row in data.iterrows():
        cached_row = []
        for cell in row:
            if isinstance(cell, str) and cell.strip():
                try:
                    cached_row.append(json.loads(cell))
                except json.JSONDecodeError:
                    cached_row.append(None)
            else:
                cached_row.append(None)
        cached_data.append(cached_row)
    return cached_data

# İki veri seti için JSON verilerini önbelleğe alıyoruz
cached_icerik1 = cache_json_data(icerik1)
cached_icerik2 = cache_json_data(icerik2)

# Zemberek'i başlatma ve bileşenlerini içe aktarma
jpype.startJVM("-Djava.class.path=/path/to/zemberek-full.jar")
from zemberek.tokenization import TurkishTokenizer
from zemberek.morphology import TurkishMorphology

# Zemberek bileşenleri
tokenizer = TurkishTokenizer.DEFAULT
morphology = TurkishMorphology.create_with_defaults()

# Lemmatizasyon fonksiyonu
def lemmatize(text):
    tokens = tokenizer.tokenize(JString(text))
    lemmas = []
    for token in tokens:
        results = morphology.analyze(token.content)
        for result in results:
            lemmas.append(result.get_stem())  # get_stem() metodunu kullanarak düzeltildi
    return " ".join(lemmas)

# Metin benzerliğini hesaplamak için fonksiyon
def compute_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    lemma1 = lemmatize(text1)
    lemma2 = lemmatize(text2)
    ratio = SequenceMatcher(None, lemma1, lemma2).ratio()
    return ratio

# Eşleştirme fonksiyonu
def match_rooms(cached_data1, cached_data2):
    matches = []
    for index1, row1 in enumerate(cached_data1):
        for col1, room1 in enumerate(row1):
            if room1 is None or 'Name' not in room1 or 'Description' not in room1:
                continue
            best_match = [0, 0, 0.0]  # [icerik2_satir_no, icerik2_sutun_no, eslesme_orani]
            for index2, row2 in enumerate(cached_data2):
                for col2, room2 in enumerate(row2):
                    if room2 is None or 'Name' not in room2 or 'Description' not in room2:
                        continue
                    # İsim ve açıklama benzerliklerini hesapla
                    similarity_name = compute_similarity(room1['Name'], room2['Name'])
                    similarity_description = compute_similarity(room1['Description'], room2['Description'])
                    overall_similarity = (similarity_name + similarity_description) / 2
                    # En iyi eşleşmeyi güncelle
                    if overall_similarity > best_match[2]:
                        best_match = [index2 + 1, col2 + 1, overall_similarity]
            # Eşleşme oranı %80 veya üzeriyse eşleşme kabul ediliyor
            if best_match[2] >= 0.8:
                matches.append([index1 + 1, col1 + 1, best_match[0], best_match[1], best_match[2]])
            else:
                matches.append([index1 + 1, col1 + 1, 0, 0, best_match[2]])
    return matches

# Zaman ölçümünü başlat
start_time = time.time()

# Verileri eşleştirelim
matches = match_rooms(cached_icerik1, cached_icerik2)

# Eşleşmeleri CSV dosyasına yazalım
match_df = pd.DataFrame(matches, columns=['icerik1_satir_no', 'icerik1_sutun_no', 'icerik2_satir_no', 'icerik2_sutun_no', 'eslesme_orani'])
match_df.to_csv(output_path, index=False)

# Zaman ölçümünü bitir ve süreyi yazdır
end_time = time.time()
print(f"Eşleşmeler {output_path} dosyasına yazıldı.")
print("--- %s seconds ---" % (end_time - start_time))

# JVM'i kapatma
jpype.shutdownJVM()
