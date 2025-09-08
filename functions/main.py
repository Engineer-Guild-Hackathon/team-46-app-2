from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore
import json
import os

# どうしてもローカルで認証が通らなかったので脳筋おまじない
if os.name=="nt":
    credential_path = "C:/Users/ymats/AppData/Roaming/gcloud/application_default_credentials.json"
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

initialize_app()
db = firestore.client()

@https_fn.on_request()
def getBooks(req: https_fn.Request) -> https_fn.Response:
    try:
        search = req.args.get("search", "")
        start = int(req.args.get("start", 0))
        size = int(req.args.get("size", 100))

        books_ref = db.collection('books')
        query = books_ref.where("title", ">=", search).where("title", "<=", search + "\uf8ff")
        
        docs = query.offset(start).limit(size).stream()

        books = {}
        for doc in docs:
            book_data = doc.to_dict()
            books[doc.id] = {
                "title": book_data.get("title"),
                "thumbnail": book_data.get("thumbnail"),
                "url": book_data.get("url")
            }

        return https_fn.Response(json.dumps(books), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Error fetching items from Firestore: {e}")
        return https_fn.Response("Internal Server Error", status=500)

@https_fn.on_request()
def getText(req: https_fn.Request) -> https_fn.Response:
    """Gets the text of a specific page of a book."""
    try:
        book_id = req.args.get("bookId")
        page = int(req.args.get("page"))
        level = req.args.get("level", "ORIGINAL")

        if not book_id or not page:
            return https_fn.Response("Missing required parameters", status=400)

        texts_ref = db.collection('texts')
        query = texts_ref.where("bookId", "==", book_id).where("page", "==", page).where("level", "==", level)
        docs = query.stream()

        text_data = {}
        for doc in docs:
            data = doc.to_dict()
            text_data["text"] = data.get("text")
            break

        return https_fn.Response(json.dumps(text_data), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Error fetching text from Firestore: {e}")
        return https_fn.Response("Internal Server Error", status=500)