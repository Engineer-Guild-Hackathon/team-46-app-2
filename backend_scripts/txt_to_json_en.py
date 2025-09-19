import json
import os

# --- 設定 ---
# 変換したいテキストファイルのフルパスを指定
# Windows例: 'C:\\Users\\YourName\\Documents\\input_homes_en.txt'
# Mac/Linux例: '/Users/YourName/Documents/input_homes_en.txt'
input_file_path = r'/home/tanipon/projects/team-46-app-2/backend_scripts/input_homes_en.txt' # ここにご自身のファイルパスを設定してください

# 出力するJSONファイルのフルパスを指定
# この例では、入力ファイルと同じフォルダに 'output.json' という名前で保存します
output_folder = os.path.dirname(os.path.abspath(input_file_path))
output_file_path = os.path.join(output_folder, 'output.json')
# -----------

# 処理を実行
try:
    # 1. ファイル全体を一つの文字列として読み込む
    with open(input_file_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # 2. 空行（2つ以上の連続した改行）を区切りとして、テキストを段落のリストに分割
    paragraphs_raw = full_text.split('\n\n')

    # 3. 各段落内の改行をスペースに置換し、前後の不要な空白を削除
    #    中身が空になった要素はリストから除外する
    chunks = [p.replace('\n', ' ').strip() for p in paragraphs_raw if p.strip()]

    # 4. JSONファイルに書き込む
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=4)

    print("✅ 変換が完了しました。（段落ごと）")
    print(f"入力: {input_file_path}")
    print(f"出力: {output_file_path}")

except FileNotFoundError:
    print(f"❌ エラー: 入力ファイル '{input_file_path}' が見つかりません。パスが正しいか確認してください。")
except Exception as e:
    print(f"❌ エラーが発生しました: {e}")