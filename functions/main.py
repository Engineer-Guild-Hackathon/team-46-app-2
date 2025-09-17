from firebase_functions import https_fn, options
from firebase_functions.options import CorsOptions
from firebase_admin import initialize_app, firestore
import json
import os
import libs
import random
import pickle
import userRateLib

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
        is_difficult_btn=req.args.get("difficultBtn","false").lower()=="true"
        
        requested_char_count=int(req.args.get("charCount",800))

        print('---> request accepted')
        docs=db.collection('access_logs').where('userId', '==', user_id).where('type','==','openWord').stream()
        clicked_word_set=set()
        print('---> got access logs')
        for doc in docs:
            print(doc)
            data= doc.to_dict()
            tmp=data.get('value',"").split(',')
            clicked_word=tmp[0]
            if len(tmp)>=2:
                level=tmp[1]
            else:
                level='unknown'
            clicked_word_set.add((clicked_word,level))
        
        clicked_word_lst=list(clicked_word_set)
        doc=db.collection('user_read').document(user_id).get()
        ur_data = doc.to_dict()
        print('---> got user_read data')
        user_rate=userRateLib.calcRate(start_sentence_no,ur_data,clicked_word_lst,is_difficult_btn)
        print('---> calculated rate:',user_rate)


        level_to_rate = { # https://www.eiken.or.jp/cse/ を参考
            "A1":1700,
            "A2":1950,
            "B1":2300,
            "B2":2600,
            "ORIGINAL":2900,
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
            jp_text=data.get("jp_segment")
            en_word=data.get(f"jp_wordorigin_{level}")
            jp_word=data.get(f"jp_word_{level}")
            word_difficulty=data.get(f"jp_worddiff_{level}")
            is_paragraph_start=data.get("is_paragraph_start", False)
            is_paragraph_end=data.get("is_paragraph_end", False)

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
                "jp":jp_text,
                "en":en_text,
                "en_word":en_word,
                "jp_word":jp_word,
                "word_difficulty":word_difficulty,
                "is_paragraph_start":is_paragraph_start,
                "is_paragraph_end":is_paragraph_end,
            })
            
        output["endSentenceNo"]=sentence_no

        print('---> done making output / start logging...')

        # logging
        if user_id != "anonymous":
            user_read_ref = db.collection('user_read').document(user_id)
            try:
                user_read_doc = user_read_ref.get()
                send_text_lst = []
                send_level_lst=[]
                if user_read_doc.exists:
                    user_read_data = user_read_doc.to_dict()
                    if user_read_data and 'send_text_lst' in user_read_data:
                        send_text_lst = user_read_data.get('send_text_lst', [])
                    if user_read_data and 'send_level_lst' in user_read_data:
                        send_level_lst = user_read_data.get('send_level_lst', [])


                new_texts =  ['|@|'.join(item['en_word']) for item in output['text']]
                new_levels = ['|@|'.join(item['word_difficulty']) for item in output['text']]
                
                
                end_pos = start_sentence_no + len(new_texts)

                if len(send_text_lst) < end_pos:
                    send_text_lst.extend(["" for _ in range(end_pos - len(send_text_lst))])
                    send_level_lst.extend(["" for _ in range(end_pos - len(send_level_lst))])

                # Place the new texts into the list using slicing
                send_text_lst[start_sentence_no:end_pos] = new_texts
                send_level_lst[start_sentence_no:end_pos] = new_levels

                user_read_ref.set({'send_text_lst': send_text_lst,'send_level_lst':send_level_lst,'rate':user_rate}, merge=True)
                
            except Exception as e:
                print(f"Error logging user read data: {e}")



        return https_fn.Response(json.dumps(output), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Error: {e}")
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
