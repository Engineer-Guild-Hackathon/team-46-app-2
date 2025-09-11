# API仕様書

## getBooks
### 概要
検索ワードをタイトルに含む書籍一覧を取得
### エンドポイント
```
/api/books
```
### パラメータ
| 名前 | 必須 | 説明 |デフォルト値|
|------|------|------|------------|
|search|      | 検索キーワード||
|start |      | 返す結果の初めのインデックス|0|
|size  |      | 返す結果の数 |100|
|sort  |      | recommended, popularity, year |recommended|
### レスポンス形式
```
{
    "book_id":{
        "title":本のタイトル,
        "thumbnail":本のサムネイルのURL,
        "url":原作のURL,
    },
}
```
### 技術仕様
firebase のbooksコレクション内でtitleにsearchパラメータを含むものを検索。うちstart番目からstart+size番目までをjson形式で返す


## getText
### 概要
あるページの本文を取得
### エンドポイント
```
/api/text
```
### パラメータ
| 名前 | 必須 | 説明 |デフォルト値|
|------|------|------|------------|
|bookId| 必須 | bookId||
|startSentenceNo| 必須 | 開始のsentenceNo||
|userId|必須|ユーザーID||
|wordClickCount||クリックして単語を表示させた回数|null|
|sentenceClickCount||クリックして日本語訳を表示させた回数|null|
|time||前回のロードから今回のリクエストまでの秒数|null|
|rate||ユーザーの推定レート|null|

### レスポンス形式
```
{
    "rate":1800,
    "endSentenceNo":121,
    "text":[
        {
            "type":"text",
            "en":"Alice said,\"I feel strange.I am getting very small\" ",
            "jp":"アリスは「体が小さくなっていくよう！」と言いました"
        },.....
    ]
}
```

- startSentenceNoから1ページ分の文のリストを返送
- type は text もしくは subtitle

### 技術仕様
firebase のtextsコレクション内で bookId,page,levelが一致するドキュメントのtextを返す。なければ空のjsonを返す

