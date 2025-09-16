# API仕様書

## getBooks
### 概要
検索ワードをタイトルに含む書籍一覧を取得
### エンドポイント
```
/books
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
/text
```
### パラメータ
| 名前 | 必須 | 説明 |デフォルト値|
|------|------|------|------------|
|bookId| 必須 | bookId||
|startSentenceNo|    | 開始のsentenceNo|0|
|userId|  |ユーザーID|"anonymous"|
|charCount||要求文字数（最大）|800|
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
            "sentenceNo":data.get("sentenceNo"),
            "en":"Alice said,\"I feel strange.I am getting very small\" ",
            "jp_word":"アリス,言う,「,私,感じる,妙に/変な,私,,○○になっていく,非常に,小さい",
            "jp":"アリスは「体が小さくなっていくよう！」と言いました"
        },.....
    ]
}
```

- startSentenceNoから1ページ分の文のリストを返送
- リスト長さはの合計文字数が要求文字数に達しない最大値
- type は text もしくは subtitle
- jp_wordは英文を ```,."!?;:()[]{}```でsplitしたものに対して1:1で対応
### 技術仕様
firebase のtextsコレクション内で bookId,page,levelが一致するドキュメントのtextを返す。なければ空のjsonを返す


## Feedback
```
/feedback
```

### パラメータ
| 名前 | 必須 | 説明 |デフォルト値|
|------|------|------|------------|
|userId|必須| ユーザーID||
|rate|必須| ユーザーレート||
|type|必須| フィードバックの種類||
|value|| ユーザーレート|""|
### レスポンス形式
```
{
    "result":"success"
}
```

### type - フィードバックの種類
```
- openJapanese（文の日本語訳を表示）
- openWord （単語の意味を表示）
- difficultBtn（「難しい」ボタンを押した）
- howWasIt（文の最後に示す難易度評価 valueはeasy|normal|difficult）
```
その他自由に追加してかまいません。

### 技術仕様
firesotreの```access_logs```コレクションに保存

