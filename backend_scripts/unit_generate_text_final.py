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
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
OUTPUT_FILENAME = "alice_detailed_analysis.json"
GUTENBERG_URL = "https://www.gutenberg.org/files/11/11-0.txt"
KANJI_JSON_PATH = r"/home/tanipon/projects/team-46-app-2/backend_scripts/alice_kanji_version.json" # 前提となる日本語訳ファイル
MAX_ITEMS_TO_PROCESS = 25

# --- 初期設定・データ準備関数 (変更なし) ---
def download_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')

def extract_and_merge_text(url, kanji_path):
    print("Gutenbergからテキストをダウンロード中...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8-sig'
        all_text = response.text
    except requests.exceptions.RequestException as e:
        return f"Error: テキストのダウンロードに失敗しました: {e}", None
    start_marker = r'\*\*\*\s*START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*'
    end_marker = r'\*\*\*\s*END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*'
    start_match = re.search(start_marker, all_text, re.IGNORECASE | re.DOTALL)
    end_match = re.search(end_marker, all_text, re.IGNORECASE | re.DOTALL)
    if not start_match or not end_match:
        return "Error: 標準の開始/終了マーカーが見つかりませんでした。", None
    body_text = all_text[start_match.end():end_match.start()].strip()
    contents_end_marker = "CHAPTER XII.   Alice’s Evidence"
    contents_end_index = body_text.find(contents_end_marker)
    if contents_end_index == -1: return "Error: 目次の終わりを特定できませんでした。", None
    story_start_marker = "CHAPTER I"
    search_after = contents_end_index + len(contents_end_marker)
    story_start_index = body_text.find(story_start_marker, search_after)
    if story_start_index == -1: return "Error: 物語の本当の開始点（CHAPTER I）を特定できませんでした。", None
    story_text = body_text[story_start_index:]
    source_data = []
    chapter_pattern = r'(CHAPTER [IVXLCDM]+\..*?)(?=(CHAPTER [IVXLCDM]+\.|\Z))'
    chapters = re.finditer(chapter_pattern, story_text, re.DOTALL)
    for match in chapters:
        chapter_content = match.group(1).strip()
        parts = re.split(r'\r?\n\s*\r?\n', chapter_content, 1)
        if not parts: continue
        title = re.sub(r'\s+', ' ', parts[0].strip())
        if title.startswith("CHAPTER"): source_data.append({"type": "subtitle", "ORIGINAL": title})
        content = parts[1].strip() if len(parts) > 1 else ""
        if not content: continue
        paragraphs = re.split(r'\r?\n\s*\r?\n', content)
        for para in paragraphs:
            clean_para = re.sub(r'\s+', ' ', para.strip())
            if (not clean_para or re.fullmatch(r'\[.*?\]', clean_para)): continue
            source_data.append({"type": "text", "ORIGINAL": clean_para})
    print(f"原文から {len(source_data)} 個の要素（タイトルと段落）を抽出しました。")
    print(f"日本語訳ファイル '{kanji_path}' を読み込み中...")
    try:
        with open(kanji_path, 'r', encoding='utf-8') as f:
            kanji_data = json.load(f)
    except FileNotFoundError: return f"Error: 日本語訳ファイル '{kanji_path}' が見つかりません。", None
    print(f"日本語訳ファイルから {len(kanji_data)} 個の要素を読み込みました。")
    merged_data = []
    min_length = min(len(source_data), len(kanji_data))
    print(f"日本語訳が存在する {min_length} 個の要素を処理対象とします。")
    for i in range(min_length):
        item = source_data[i]
        item['jp_original'] = kanji_data[i]
        merged_data.append(item)
    print("原文と日本語訳のマージが完了しました。")
    return None, merged_data

# --- OpenAI API 呼び出し関数 (変更なし) ---
def call_openai_api(system_prompt, user_prompt, max_retries=3):
    """汎用的なOpenAI API呼び出し関数。リトライ機能とNoneチェック付き。"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            # ▼▼▼ ここが安全チェックです ▼▼▼
            response_content = response.choices[0].message.content
            if response_content is None:
                print(f"APIが空の応答を返しました (試行 {attempt + 1}/{max_retries})。再試行します...")
                time.sleep(5)
                continue # 次の再試行へ進む

            return json.loads(response_content)

        except Exception as e:
            print(f"API呼び出しでエラーが発生しました (試行 {attempt + 1}/{max_retries}): {e}")
            time.sleep(5)

    return None # すべての再試行が失敗した場合

# --- ▼▼▼ メインの処理関数群（全面的に刷新） ▼▼▼ ---

def get_aligned_segments_by_jp(paragraph_en, paragraph_jp):
    """
    日本語の「。」を基準に、対応する英文セグメントをAIに分割させる。
    失敗した場合は、原文ママ（単一セグメント）を返す。
    """
    jp_sentence_count = len([s for s in paragraph_jp.split('。') if s.strip()])
    if jp_sentence_count <= 1: # 日本語が1文以下なら分割不要
        return [paragraph_en]

    system_prompt = (
        "You are an expert bilingual aligner. Your task is to accurately segment an English paragraph based on the sentence breaks ('。') in its Japanese translation. "
        "The number of English segments in your output list MUST EXACTLY match the number of Japanese sentences. "
        "Respond ONLY in a valid JSON format with a single key 'segments' which contains a list of the extracted English text segments as strings."
    )
    user_prompt = (
        f"There are {jp_sentence_count} Japanese sentences separated by '。'. Respond with exactly {jp_sentence_count} English segments.\n\n"
        f"English Paragraph: \"{paragraph_en}\"\n"
        f"Japanese Paragraph: \"{paragraph_jp}\"\n"
    )

    # 最大2回まで試行
    for attempt in range(2):
        print(f"    - Attempting alignment (Attempt {attempt + 1}/2)...")
        response = call_openai_api(system_prompt, user_prompt)

        if response and 'segments' in response and isinstance(response['segments'], list):
            if len(response['segments']) == jp_sentence_count:
                print("      -> Alignment successful.")
                return response['segments'] # 成功：分割したセグメントを返す
            else:
                print(f"      -> Alignment failed: AI returned {len(response['segments'])} segments, expected {jp_sentence_count}. Retrying...")
                user_prompt = (
                    f"Your last response was incorrect. There are {jp_sentence_count} Japanese sentences. You MUST respond with exactly {jp_sentence_count} English segments.\n\n"
                    f"English Paragraph: \"{paragraph_en}\"\n"
                    f"Japanese Paragraph: \"{paragraph_jp}\"\n"
                )
        time.sleep(1)

    print("      -> Alignment failed after all attempts. Using original paragraph.")
    # ▼▼▼ 変更点 ▼▼▼
    # 最終的に失敗した場合は、スキップせずに原文ママを単一セグメントとして返す
    return [paragraph_en]

def get_cefr_variants(segment_en):
    """英文のCEFRバリエーションをAPIで取得します。"""
    system_prompt = (
        "You are a language education expert. Rewrite the given English sentence for CEFR levels A1, A2, B1, and B2, "
        "maintaining the core meaning. Respond ONLY in a valid JSON format with keys: 'A1', 'A2', 'B1', 'B2'."
    )
    user_prompt = f"Original Sentence: \"{segment_en}\""
    return call_openai_api(system_prompt, user_prompt)

def get_en_chunks(sentence):
    """【新関数①】AIに英文を意味の塊（チャンク）に分割させるだけのシンプルな関数"""
    system_prompt = ("You are an expert linguist. Your task is to split the given English sentence into grammatical chunks. "
                    "Follow these rules precisely:\n"
                    "1.  Keep infinitive phrases (e.g., 'to do', 'to get') and verb phrases (e.g., 'was beginning', 'ran close by') together as a single chunk.\n"
                    "2.  For simple prepositional phrases (e.g., 'with pink eyes', 'on the bank'), split them into individual words (e.g., 'with', 'pink', 'eyes').\n"
                    "3.  Nouns and their articles (e.g., 'a White Rabbit') should be a single chunk.\n"
                    "Respond ONLY in a valid JSON format with a single key 'chunks' which contains a list of strings.")
    user_prompt = f"Split this sentence into chunks according to the rules: \"{sentence}\""
    response = call_openai_api(system_prompt, user_prompt)
    if response and 'chunks' in response and isinstance(response['chunks'], list):
        return response['chunks']
    return [] # 失敗時は空リストを返す

def get_chunk_analysis(chunk_en, context_jp_segment):
    """
    AIに個別のチャンクの翻訳とCEFRレベルを分析させる。
    jp_segmentを文脈のヒントとして追加。
    """
    system_prompt = ("You are an expert linguist and translator. For the given English phrase, provide its natural Japanese translation and estimate its CEFR level. "
                    "Use the 'Japanese Context Sentence' as a hint to provide the most appropriate translation. "
                    "Respond ONLY in a valid JSON format with keys 'jp_chunk' and 'cefr_level'.")
    user_prompt = (f"Japanese Context Sentence: \"{context_jp_segment}\"\n\n"
                f"Analyze this English phrase: \"{chunk_en}\"")
    return call_openai_api(system_prompt, user_prompt)

def split_jp_sentences(text):
    """
    日本語のテキストを「。」、「！」、「？」を区切り文字として文に分割する。
    区切り文字は文末に保持される。
    """
    if not text:
        return []
    
    # 正規表現で文と区切り文字のペアに分割
    # 例: 「元気？はい。」 -> ['元気', '？', 'はい', '。', '']
    parts = re.split(r'([。！？])', text)
    
    # 文と区切り文字を結合してリストを作成
    # ['元気？', 'はい。'] のように復元する
    sentences = []
    for i in range(0, len(parts) - 1, 2):
        sentence = (parts[i] + parts[i+1]).strip()
        if sentence:
            sentences.append(sentence)
    
    # もし最後の部分にテキストが残っていたら追加（普通はないはずですが念のため）
    if len(parts) % 2 == 1 and parts[-1].strip():
        sentences.append(parts[-1].strip())

    return sentences

def main():
    """メイン処理を実行します。(SubtitleもTextと同様に詳細分析する)"""
    download_nltk_data()
    error, merged_data = extract_and_merge_text(GUTENBERG_URL, KANJI_JSON_PATH)
    if error:
        print(error)
        return

    final_results = []
    chunk_cache = {}
    items_to_process = merged_data[:MAX_ITEMS_TO_PROCESS] if MAX_ITEMS_TO_PROCESS != -1 else merged_data
    total_items = len(items_to_process)
    print(f"\n処理を開始します... (対象: {total_items} 個の要素)")

    for i, item in enumerate(items_to_process):
        print(f"\n--- Processing item {i + 1}/{total_items} ---")

        # ▼▼▼ 新しい統一処理ロジック ▼▼▼
        
        is_subtitle = item['type'] == 'subtitle'

        # SubtitleかTextかで、セグメント分割方法を切り替える
        if is_subtitle:
            print(f"  [Subtitle Found]: {item['ORIGINAL']}")
            # Subtitleの場合、セグメントはタイトルそのもの一つだけ
            segments = [item['ORIGINAL']]
            jp_sentences = [item['jp_original']]
        else:
            print(f"  [Text Paragraph]: {item['ORIGINAL'][:70]}...")
            jp_sentences_candidate = split_jp_sentences(item['jp_original'])
            print("  - Aligning segments based on Japanese translation...")
            segments = get_aligned_segments_by_jp(item['ORIGINAL'], item['jp_original'])
            time.sleep(0.5) # 待機時間を0.5秒に短縮
        
        if len(segments) != len(jp_sentences) and not is_subtitle and len(segments) > 1:
            print(f"      [Warning] Alignment failed. Using original paragraph for further processing.")

        is_paragraph_start = True
        for j, seg in enumerate(segments):
            is_paragraph_end = (j == len(segments) - 1)
            print(f"    - Segment {j + 1}/{len(segments)}: '{seg}'")
            
            # SubtitleかTextかで、CEFRレベルの生成方法を切り替える
            if is_subtitle:
                # Subtitleの場合は、A1〜B2も原文と同じにする
                cefr_variants = {"A1": seg, "A2": seg, "B1": seg, "B2": seg}
            else:
                # Textの場合は、AIで生成する
                cefr_variants = get_cefr_variants(seg)
                time.sleep(0.5)

            if not cefr_variants:
                print(f"      SKIPPING segment due to CEFR generation failure.")
                continue

            correct_jp_segment = jp_sentences[j] if j < len(jp_sentences) else ""
            result_segment = {
                "type": item['type'], # 元のタイプを保持
                "ORIGINAL_SEGMENT": seg, "jp_segment": correct_jp_segment,
                "is_paragraph_start": is_paragraph_start, "is_paragraph_end": is_paragraph_end,
                **cefr_variants
            }
            is_paragraph_start = False

            # --- ここから先のチャンク分析は、SubtitleもTextも全く同じ ---
            all_versions = {"ORIGINAL": seg, **cefr_variants}
            for level, text in all_versions.items():
                if not text: continue
                print(f"      - Analyzing {level} version: '{text}'")
                en_chunks = get_en_chunks(text)
                time.sleep(0.5)
                jp_chunks, cefr_levels = [], []
                
                if not en_chunks:
                    print(f"        Chunking for {level} failed.")
                else:
                    for chunk in en_chunks:
                        if chunk in chunk_cache:
                            analysis = chunk_cache[chunk]
                        else:
                            analysis = get_chunk_analysis(chunk, correct_jp_segment)
                            chunk_cache[chunk] = analysis
                            time.sleep(0.5)
                        
                        if analysis and 'jp_chunk' in analysis and 'cefr_level' in analysis:
                            jp_chunks.append(analysis['jp_chunk'])
                            cefr_levels.append(analysis['cefr_level'])
                        else:
                            jp_chunks.append("?")
                            cefr_levels.append("?")
                
                result_segment[f'jp_wordorigin_{level}'] = en_chunks
                result_segment[f'jp_word_{level}'] = jp_chunks
                result_segment[f'jp_worddiff_{level}'] = cefr_levels
            
            final_results.append(result_segment)

    try:
        print("\n最終結果をファイルに書き込んでいます...")
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        print(f"処理が完了しました。結果は '{OUTPUT_FILENAME}' に保存されました。")
    except IOError as e:
        print(f"\nError: ファイルの書き込みに失敗しました: {e}")

if __name__ == "__main__":
    main()