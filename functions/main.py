from firebase_functions import https_fn, options
from firebase_functions.options import CorsOptions
from firebase_admin import initialize_app, firestore
import json
import os
import libs
import random
import pickle

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
        if book_id==None:
            return https_fn.Response("Missing required parameters", status=400)

        start_sentence_no = int(req.args.get("startSentenceNo",0))
        user_id=req.args.get("userId","anonymous")
        
        requested_char_count=int(req.args.get("charCount",800))
        # word_click_count = req.args.get("wordClickCount")
        # sentence_click_count = req.args.get("sentenceClickCount")
        # time=req.args.get("time")
        # user_rate = int(req.args.get("rate",1800))

        print('---a')
        docs=db.collection('access_logs').where('userId', '==', user_id).where('type','==','openWord').stream()
        clicked_word_set=set()
        for doc in docs:
            print(doc)
            data= doc.to_dict()
            clicked_word=data.get('value',",").split(',')[1]
            clicked_word_set.add(clicked_word)
        
        clicked_word_lst=list(clicked_word_set)

        print('---b')
        doc=db.collection('user_read').document(user_id).get()
        data = doc.to_dict()
        if data==None or 'send_text_lst' not in data:
            user_rate=1800
        else:
            text_lst_2d=data['send_text_lst'][:start_sentence_no-2] #-2はマジックナンバー：リクエストの時点で「ユーザーがこれまで読んだテキスト」を取得したい
            
            word_lst=list(set(libs.MultiSplit(".".join(text_lst_2d),set(' ,."!?;:()[]{}'))))
            print(word_lst)
            print('---c')
            word_counter={
                'A1':0,
                'A2':0,
                'B1':0,
                'B2':0,
                'C1':0,
                'C2':0,
                'unknown':0,
            }
            clicked_word_counter={
                'A1':0,
                'A2':0,
                'B1':0,
                'B2':0,
                'C1':0,
                'C2':0,
                'unknown':0,
            }
            with open('en2CEFR.pkl','rb') as f:
                word2CEFR=pickle.load(f)
            print('---d')
            for word in word_lst:
                level=word2CEFR.get(word.lower(),'unknown')
                word_counter[level]+=1

            for word in clicked_word_lst:
                level=word2CEFR.get(word.lower(),'unknown')
                clicked_word_counter[level]+=1
            
            clicked_word_rate={key: clicked_word_counter[key]/(word_counter[key]+1) if word_counter[key]>=5 else None for key in word_counter.keys()}
            print(clicked_word_counter)
            print(word_counter)

            # return https_fn.Response(json.dumps(clicked_word_rate), status=200, mimetype="application/json")

            user_rate=2700

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
                return https_fn.Response(f"Internal Server Error: no level {level} sentence on DB", status=500)
            if jp_text==None:
                return https_fn.Response("Internal Server Error: no jp sentence on DB", status=500)
            if jp_word==None:
                return https_fn.Response(f"Internal Server Error: no jp_word_{level} sentence on DB", status=500)

            totalCharaCount+=len(en_text)
            if totalCharaCount>requested_char_count and len(output["text"])>=1:
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
        if user_id != "anonymous":
            user_read_ref = db.collection('user_read').document(user_id)
            try:
                user_read_doc = user_read_ref.get()
                send_text_lst = []
                if user_read_doc.exists:
                    user_read_data = user_read_doc.to_dict()
                    if user_read_data and 'send_text_lst' in user_read_data:
                        send_text_lst = user_read_data.get('send_text_lst', [])

                new_texts = [item['en'] for item in output['text']]
                
                end_pos = start_sentence_no + len(new_texts)

                if len(send_text_lst) < end_pos:
                    send_text_lst.extend(["" for _ in range(end_pos - len(send_text_lst))])

                # Place the new texts into the list using slicing
                send_text_lst[start_sentence_no:end_pos] = new_texts

                user_read_ref.set({'send_text_lst': send_text_lst}, merge=True)
            except Exception as e:
                print(f"Error logging user read data: {e}")

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
