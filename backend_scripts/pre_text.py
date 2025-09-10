import requests
import re
import json
import nltk

def download_nltk_data():

    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab')

def preprocess_gutenberg_text(url):
    """
    Project Gutenbergのテキストをダウンロードし、章ごとに構造化して文に分割。
    NLTKの分割結果をさらに後処理して精度を向上。
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8-sig'
        all_text = response.text
    except requests.exceptions.RequestException as e:
        print(f"Error: テキストのダウンロードに失敗しました: {e}")
        return None

    try:
        flags = re.IGNORECASE | re.DOTALL
        start_marker_match = re.search(r'\*\*\*\s*START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*', all_text, flags)
        end_marker_match = re.search(r'\*\*\*\s*END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*', all_text, flags)

        if not start_marker_match or not end_marker_match:
            print("Warning: 標準の開始/終了マーカーが見つかりません")
            return None
        
        start_index = start_marker_match.end()
        end_index = end_marker_match.start()
        body_text = all_text[start_index:end_index].strip()
        
    except Exception as e:
        print(f"Error: 本文の抽出中にエラーが発生: {e}")
        return None

    chapter_split_pattern = r'(CHAPTER [IVXLCDM]+\.\s+.*?(?=\n|\r))'
    parts = re.split(chapter_split_pattern, body_text)
    
    structured_data = []
    chapter_number = 1
    
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        content = parts[i+1]
        
        clean_content = re.sub(r'\s+', ' ', content).strip()
        sentences = nltk.sent_tokenize(clean_content)
        
        # --- NLTKの分割ミスを補正する後処理ロジック ---
        corrected_sentences = []
        for sentence in sentences:
            # 1. 引用符/感嘆符/疑問符の直後で、大文字や引用符で始まる単語の前で分割
            sentence = re.sub(r'(?<=[?”!])\s+(?=[A-Z“])', '\n', sentence)

            # 2. アスタリスク行を独立させる
            sentence = re.sub(r'(\s*(\*\s*){3,}\s*)', r'\n\1\n', sentence)

            # 3. 擬音語や特定のフレーズを独立させる
            sentence = re.sub(r'\b(thump!|splash!)\b', r'\n\1\n', sentence)
            sentence = re.sub(r'(Down, down, down\.)', r'\n\1\n', sentence)
            
            # 改行で最終的に分割し、リストに追加
            for sub_sentence in sentence.split('\n'):
                sub_sentence = sub_sentence.strip()
                # アスタリスクだけの行は最終結果から除外
                if sub_sentence and not re.fullmatch(r'(\*\s*)+', sub_sentence):
                    corrected_sentences.append(sub_sentence)
        
        cleaned_sentences = [s.strip() for s in corrected_sentences if s.strip()]
        
        if cleaned_sentences:
            structured_data.append({
                "chapter_number": chapter_number,
                "title": title,
                "sentences": cleaned_sentences
            })
            chapter_number += 1
            
    return structured_data

def main():
    """
    メイン処理を実行します。
    """
    download_nltk_data()
    
    target_url = "https://www.gutenberg.org/cache/epub/11/pg11.txt"
    structured_chapters = preprocess_gutenberg_text(target_url)

    if structured_chapters:
        print(f"\n成功: テキストを {len(structured_chapters)} 個の章に分割しました。")
        
        output_filename = "alice_chapters_structured.json"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(structured_chapters, f, indent=2, ensure_ascii=False)
            print(f"結果を '{output_filename}' に保存しました。")
            
            print("\n--- 最初の章の情報 ---")
            first_chapter = structured_chapters[0]
            print(f"章番号: {first_chapter['chapter_number']}")
            print(f"タイトル: {first_chapter['title']}")
            print("--- 最初の10文 ---")
            for sentence in first_chapter['sentences'][:10]:
                print(sentence)
            print("------------------")

        except IOError as e:
            print(f"Error: ファイルの書き込みに失敗しました: {e}")

if __name__ == "__main__":
    main()

