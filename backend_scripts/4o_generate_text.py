import os
import json
import time
import re
import requests
import nltk
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# --- 設定項目 ---

# 1. OpenAI APIキーの設定
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 2. ファイル名
OUTPUT_FILENAME = "alice_variants_with_jp.json"
GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/11/pg11.txt"

# 3. 安全装置
MAX_ITEMS_TO_PROCESS = -1


def download_nltk_data():
    """NLTKの分割モデルをダウンロードします。"""
    for model in ['punkt', 'punkt_tab']:
        try:
            nltk.data.find(f'tokenizers/{model}')
        except LookupError:
            nltk.download(model)


def extract_and_flatten_text(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8-sig'
        all_text = response.text
    except requests.exceptions.RequestException as e:
        return f"Error: テキストのダウンロードに失敗しました: {e}", None

    flags = re.IGNORECASE | re.DOTALL
    start_marker = r'\*\*\*\s*START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*'
    end_marker = r'\*\*\*\s*END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*'
    
    start_match = re.search(start_marker, all_text, flags)
    end_match = re.search(end_marker, all_text, flags)

    if not start_match or not end_match:
        return "Error: 標準の開始/終了マーカーが見つかりませんでした。", None
    
    body_text = all_text[start_match.end():end_match.start()].strip()
    
    # ★★★ ここからが修正済みの安定版ロジックです ★★★
    # 以前の安定した方法で、章ごとの大きな塊を見つけます
    chapter_pattern = r'(CHAPTER [IVXLCDM]+\..*?)(?=(CHAPTER [IVXLCDM]+\.|$))'
    chapters = re.finditer(chapter_pattern, body_text, re.DOTALL)
    
    flat_list = []
    for match in chapters:
        chapter_content = match.group(1).strip()
        
        # 最初の「空白行」で、複数行のタイトルと本文を正確に分割します
        parts = re.split(r'\r?\n\s*\r?\n', chapter_content, 1)
        
        if not parts:
            continue
            
        # タイトル部分の改行をスペースに置換して、1行の綺麗なタイトルにします
        title = re.sub(r'\s+', ' ', parts[0].strip())
        
        # 本文部分を取得します
        content = parts[1].strip() if len(parts) > 1 else ""

        # 目次など、本文がない章タイトルは無視します
        if not content:
            continue
            
        if title:
            flat_list.append({"type": "subtitle", "ORIGINAL": title})

        paragraphs = re.split(r'\r?\n\s*\r?\n', content)
        
        for paragraph in paragraphs:
            clean_paragraph = re.sub(r'\s+', ' ', paragraph.strip())
            if not clean_paragraph:
                continue
            
            sentences = nltk.sent_tokenize(clean_paragraph)
            
            for i, sentence in enumerate(sentences):
                is_paragraph_start = (i == 0)
                is_paragraph_end = (i == len(sentences) - 1)
                
                if sentence.strip() and not re.fullmatch(r'(\*\s*)+', sentence.strip()):
                    item = {
                        "type": "text", 
                        "ORIGINAL": sentence.strip(),
                        "is_paragraph_start": is_paragraph_start,
                        "is_paragraph_end": is_paragraph_end
                    }
                    flat_list.append(item)
    
    return None, flat_list

# api処理
def get_ai_variants(item, previous_item_text=""):
    """要素の種類に応じてOpenAI APIを呼び出し、結果を返します。"""
    original_text = item["ORIGINAL"]
    item_type = item["type"]
    
    if item_type == "text":
        system_prompt = (
            "You are an expert linguist and translator. Your task is to process the 'Target Sentence'. "
            "1. Rewrite it into four distinct versions for CEFR levels A1, A2, B1, and B2, maintaining the original meaning. "
            "2. Provide a natural-sounding Japanese translation. "
            "Use the 'Previous Sentence' for context. "
            'Respond ONLY in a valid JSON format with the keys: "A1", "A2", "B1", "B2", "jp".'
        )
        user_prompt = (
            f"Previous Sentence: \"{previous_item_text}\"\n"
            f"Target Sentence: \"{original_text}\""
        )
    elif item_type == "subtitle":
        system_prompt = (
            "You are an expert translator. Your task is to translate the given 'Chapter Title' "
            "into a natural-sounding Japanese title. "
            'Respond ONLY in a valid JSON format with a single key: "jp".'
        )
        user_prompt = f"Chapter Title: \"{original_text}\""
    else:
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        api_result = json.loads(response.choices[0].message.content)

        if item_type == "subtitle":
            api_result["A1"] = original_text
            api_result["A2"] = original_text
            api_result["B1"] = original_text
            api_result["B2"] = original_text
        
        return api_result

    except Exception as e:
        return None

#メイン処理
def main():
    """メイン処理を実行します。"""
    download_nltk_data()
    
    error, source_data = extract_and_flatten_text(GUTENBERG_URL)
    if error:
        print(error)
        return
    
    final_results = []
    previous_item_text = ""
    
    items_to_process = source_data
    if MAX_ITEMS_TO_PROCESS != -1:
        items_to_process = source_data[:MAX_ITEMS_TO_PROCESS]

    for item in items_to_process:
        variants = get_ai_variants(item, previous_item_text)
        
        if variants:
            item.update(variants)
            final_results.append(item)

        if item["type"] == "text":
            previous_item_text = item["ORIGINAL"]
            
        time.sleep(1)

    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"\nError: ファイルの書き込みに失敗しました: {e}")

if __name__ == "__main__":
    main()

