import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# --- OpenAI APIクライアントの初期化 ---
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except TypeError:
    print("エラー: OpenAI APIキーが設定されていません。")
    print(".envファイルに 'OPENAI_API_KEY=\"sk-...\"' と記述してください。")
    exit()


def read_and_clean_text_from_file(filepath="input.txt"):
    """
    指定されたテキストファイルを読み込み、不要な文字を掃除して段落のリストを返す。
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"エラー: テキストファイル '{filepath}' が見つかりません。")
        print("プログラムと同じフォルダにファイルを作成し、文章を貼り付けてください。")
        return None

    cleaned_paragraphs = []
    for line in lines:
        cleaned_line = re.sub(r'^[□■\s]+', '', line).strip()
        if cleaned_line:
            cleaned_paragraphs.append(cleaned_line)
            
    return cleaned_paragraphs


def convert_to_kanji_with_openai(text_to_convert):
    """
    OpenAI APIを使用して、与えられたテキストのひらがなを適切な漢字に変換する。
    """
    if not client.api_key:
        return f"（APIキー未設定のため変換スキップ）{text_to_convert}"

    system_prompt = "あなたは日本語の文章を編集する専門家です。受け取った文章について、子供向けにひらがなで書かれている単語を、文脈に合った自然な漢字に変換してください。ただし、セリフの雰囲気や文体は変更せず、元の文章の良さを維持してください。"
    
    try:
        print(f"変換中: 「{text_to_convert[:20]}...」")
        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_to_convert}
            ],
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"!! OpenAI APIでエラーが発生しました: {e}")
        return f"（APIエラーのため変換失敗）{text_to_convert}"

# --- メイン処理 ---
def main():
    filepath = r"/home/tanipon/projects/team-46-app-2/backend_scripts/input_homes.txt"
    original_paragraphs = read_and_clean_text_from_file(filepath)
    
    if not original_paragraphs:
        print("処理を終了します。")
        return

    print(f"テキストファイルを読み込みました。合計 {len(original_paragraphs)} 段落を処理します。")
    
    kanji_converted_paragraphs = []
    for para in original_paragraphs:
        # ▼▼▼【変更点】数字とピリオドで始まる行はタイトルとみなし、変換しない ▼▼▼
        if re.match(r'^\d+\.\s*', para):
            print(f"タイトルを検出（変換スキップ）: 「{para}」")
            kanji_converted_paragraphs.append(para)
        else:
            converted_para = convert_to_kanji_with_openai(para)
            kanji_converted_paragraphs.append(converted_para)
        # ▲▲▲ 変更ここまで ▲▲▲

    final_json = json.dumps(kanji_converted_paragraphs, ensure_ascii=False, indent=2)
    
    with open("alice_kanji_version.json", "w", encoding="utf-8") as f:
        f.write(final_json)
        
    print("\n--- 処理完了 ---")
    print("変換後のテキストを 'alice_kanji_version.json' ファイルに保存しました。")


if __name__ == "__main__":
    main()