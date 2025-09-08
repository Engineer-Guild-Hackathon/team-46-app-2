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
|page  | 必須 | ページ番号||
|level |      | CEFRレベル（A1-B2,ORIGINAL） |ORIGINAL|

### レスポンス形式
```
{
    "text":本文
}
```
### 技術仕様
firebase のtextsコレクション内で bookId,page,levelが一致するドキュメントのtextを返す。なければ空のjsonを返す

# FireStoreデータ構造（参考）
- books(id=bookId)
    - title: str
    - thumbnail: str
    - url: str
- texts
    - bookId: str
    - page: int
    - level: str
    - text: str