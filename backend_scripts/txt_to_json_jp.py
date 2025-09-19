import json
import os # ファイルパスを扱うためにosモジュールをインポート

# --- 設定 ---
# 変換したいテキストファイルのフルパスを指定
# Windows例: 'C:\\Users\\YourName\\Documents\\input.txt'
# Mac/Linux例: '/Users/YourName/Documents/input.txt'
input_file_path = r'/home/tanipon/projects/team-46-app-2/backend_scripts/input_homes.txt'

# 出力するJSONファイルのフルパスを指定
# この例では、入力ファイルと同じフォルダに 'output.json' という名前で保存します
output_folder = os.path.dirname(input_file_path)
output_file_path = os.path.join(output_folder, 'output.json')
# -----------

# 処理を実行
try:
    # 1. テキストファイルを読み込む
    with open(input_file_path, 'r', encoding='utf-8') as f:
        # 空行を除外してリストに格納
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # 2. JSONファイルに書き込む
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(lines, f, ensure_ascii=False, indent=4)

    print("✅ 変換が完了しました。")
    print(f"入力: {input_file_path}")
    print(f"出力: {output_file_path}")

except FileNotFoundError:
    print(f"❌ エラー: 入力ファイル '{input_file_path}' が見つかりません。パスが正しいか確認してください。")
except Exception as e:
    print(f"❌ エラーが発生しました: {e}")