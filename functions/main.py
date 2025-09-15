from firebase_functions import https_fn, options
from firebase_functions.options import CorsOptions
from firebase_admin import initialize_app, firestore
import json
import os
import libs
import random

# どうしてもローカルで認証が通らなかったので脳筋おまじない
if os.name=="nt":
    credential_path = "C:/Users/ymats/AppData/Roaming/gcloud/application_default_credentials.json"
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

initialize_app()
db = firestore.client()

@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "OPTIONS"]))
def books(req: https_fn.Request) -> https_fn.Response:
    try:
        search = req.args.get("search", "")
        start = int(req.args.get("start", 0))
        size = int(req.args.get("size", 100))
        sort = req.args.get("sort", "recommended")

        books_ref = db.collection('books')
        query = books_ref

        if search:
            query = query.where("title", ">=", search).where("title", "<=", search + "\uf8ff")
        
        if sort == "popularity":
            query = query.order_by("views", direction=firestore.Query.DESCENDING)
        elif sort == "year":
            query = query.order_by("published", direction=firestore.Query.DESCENDING)
        
        docs = query.offset(start).limit(size).stream()

        books = {}
        for doc in docs:
            book_data = doc.to_dict()
            books[doc.id] = {
                "title": book_data.get("title"),
                "thumbnail": book_data.get("thumbnail"),
                "url": book_data.get("url"),
                "author": book_data.get("author")
            }

        return https_fn.Response(json.dumps(books), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Error fetching items from Firestore: {e}")
        return https_fn.Response("Internal Server Error", status=500)

@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "OPTIONS"]))
def text(req: https_fn.Request) -> https_fn.Response:
    """Gets the text of a specific page of a book."""
    try:
        book_id = req.args.get("bookId")
        start_sentence_no = int(req.args.get("startSentenceNo",0))
        user_id=req.args.get("userId","anonymous")
        requested_char_count=int(req.args.get("charCount",800))
        word_click_count = req.args.get("wordClickCount")
        sentence_click_count = req.args.get("sentenceClickCount")
        # time=req.args.get("time")
        user_rate = int(req.args.get("rate",1800))

        if book_id==None:
            return https_fn.Response("Missing required parameters", status=400)

        # ユーザレートの更新ロジック
        if word_click_count==None and sentence_click_count==None:
            # レベル変動なし
            pass
        else:
            if word_click_count==None:
                cnt=int(sentence_click_count)
            elif sentence_click_count==None:
                cnt=int(word_click_count)
            else:
                cnt=int(word_click_count)+int(sentence_click_count)
            if cnt == 0:
                user_rate += 200
            elif cnt ==1:
                user_rate += 0
            elif cnt ==2:
                user_rate -= 100
            elif cnt <=4:
                user_rate -= 200
            else:
                user_rate -= 300
        
        level_to_rate = { # https://www.eiken.or.jp/cse/ を参考
            "A1":1500,
            "A2":1800,
            "B1":2100,
            "B2":2400,
            "ORIGINAL":2700,
        }

        choices,weights=libs.getWeight(user_rate, level_to_rate)

        output = {
            "rate": user_rate,
            "text":[],
        }



        texts_ref = db.collection('text')
        query = texts_ref.where("bookId", "==", book_id) \
            .where("sentenceNo", ">=", start_sentence_no) \
            .where("sentenceNo", "<=", start_sentence_no+20) \
            .order_by("sentenceNo", direction=firestore.Query.ASCENDING) \

        docs = query.stream()

        sentence_no=0
        totalCharaCount=0
        for doc in docs:
            data = doc.to_dict()

            level=random.choices(choices, weights=weights, k=1)[0]

            en_text=data.get(level)
            jp_text=data.get("jp")
            jp_word=data.get(f"jp_word_{level}")
            sentence_no=data.get("sentenceNo")

            if en_text==None:
                return https_fn.Response("Internal Server Error: no level {level} sentence on DB", status=500)
            if jp_text==None:
                return https_fn.Response("Internal Server Error: no jp sentence on DB", status=500)
            if jp_word==None:
                return https_fn.Response("Internal Server Error: no jp_word_{level} sentence on DB", status=500)

            totalCharaCount+=len(en_text)
            if totalCharaCount>requested_char_count:
                break

            output["text"].append({
                "type":data.get("type","text"),
                "sentenceNo":sentence_no,
                "en":en_text,
                "jp":jp_text,
                "jp_word":jp_word,
            })
            
        output["endSentenceNo"]=sentence_no

        # logging
        db.collection('access_logs').add({
            'userId': user_id,
            'bookId': book_id,
            'startSentenceNo': start_sentence_no,
            'userRate': user_rate,
            'wordClickCount': word_click_count,
            'sentenceClickCount': sentence_click_count,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'type':'fetchText',
        })

        return https_fn.Response(json.dumps(output), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Error fetching text from Firestore: {e}")
        return https_fn.Response("Internal Server Error", status=500)

@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "OPTIONS"]))
def feedback(req: https_fn.Request) -> https_fn.Response:
    try:
        if req.method == 'POST':
            data = req.get_json()
            user_id = data.get("userId")
            rate = data.get("rate")
            feedback_type=data.get("type","general")
            value=data.get("value","")
        else: # GET
            user_id = req.args.get("userId")
            rate = req.args.get("rate")
            feedback_type=req.args.get("type","general")
            value=req.args.get("value","")


        if not all([user_id, rate]):
            return https_fn.Response("Missing required parameters", status=400)

        db.collection('access_logs').add({
            'userId': user_id,
            'rate': rate,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'type':feedback_type,
            'value':value,
        })

        return https_fn.Response(json.dumps({"result": "success"}), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Error logging difficult button event: {e}")
        return https_fn.Response("Internal Server Error", status=500)
