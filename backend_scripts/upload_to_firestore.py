"""
data/ 下の JSON ファイルをすべて Firestore にアップロードするスクリプト
JSONの形式:
```
[
    {
         "type":"text",
         "ORIGINAL":"(ORIGINAL)This is the 1st sentence of the Alice book.",
         "A1":"(A1)This is the 1st sentence of the Alice book.",
         "A2":"(A2)This is the 1st sentence of the Alice book.",
         "B1":"(B1)This is the 1st sentence of the Alice book.",
         "B2":"(B2)This is the 1st sentence of the Alice book.",
         "is_paragraph_start": true,  // type:textの時のみ
         "is_paragraph_end": true,    // type:textの時のみ
         "jp":"これはアリス本の1文目です。"
     },....
]
```
各要素(ditc)に対して以下の二項目を追加してアップロード
- bookId: ファイル名(拡張子なし)
- sentenceNo: 連番(0から始まる)
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# どうしてもローカルで認証が通らなかったので脳筋おまじない
if os.name=="nt":
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "C:/Users/ymats/AppData/Roaming/gcloud/application_default_credentials.json"
    os.environ['GOOGLE_CLOUD_PROJECT'] = "flexread-egh"

def main():
    # Firebase Admin SDKの初期化
    # GOOGLE_APPLICATION_CREDENTIALS 環境変数が設定されていることを前提とする
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

    db = firestore.client()

    # データディレクトリのパス
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # データディレクトリ内のすべてのファイルをループ
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            book_id = os.path.splitext(filename)[0]
            file_path = os.path.join(data_dir, filename)

            print(f"Processing {file_path}...")

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # バッチ書き込みの準備
            batch = db.batch()
            collection_ref = db.collection('text')

            # 各文に対して処理
            for i, item in enumerate(data):
                item['bookId'] = book_id
                item['sentenceNo'] = i

                # ドキュメントIDを bookId と sentenceNo で作成
                doc_id = f"{book_id}{i}"
                doc_ref = collection_ref.document(doc_id)
                batch.set(doc_ref, item)

            # バッチをコミット
            batch.commit()
            print(f"Successfully uploaded {len(data)} sentences for bookId: {book_id}")

if __name__ == "__main__":
    main()
