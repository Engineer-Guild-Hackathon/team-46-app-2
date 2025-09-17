#import matplotlib.pyplot as plt

from math import log
def probSigmoid(x,rate):
    def f(x):
        return x/(1+abs(x))
    return (f((x-rate-100)/100)+1)/2

def calcRate(start_sentence_no,ur_data,clicked_word_lst,is_difficult_btn):
    """
    start_sentence_no: int
    ur_data: firestoreのuser_readドキュメントの内容
             {
                rate:1800,
                send_text_lst:"Alice|@|was starting|@|to feel|@|very tired|@|fr....","She|@|checked|@|her sister's b..."
                send_level_lst:["A1|@|B1|@|A2|@|A2|@|A2|@|A2|@|A1|@|B1|@|A2","A1|@|B1|@|A1|@|A2|@|B1|@|A2|@|A2|@|A1|@|A2"...]
             }
    clicked_word_lst: [(word,level),...]
    is_difficult_btn: bool
    """

    now_user_rate=int(ur_data.get('rate',1950))
    if is_difficult_btn:
        return now_user_rate-300
    elif ur_data==None or 'send_text_lst' not in ur_data or 'send_level_lst' not in ur_data:
        return now_user_rate

    text_lst_2d=ur_data['send_text_lst'][:max(start_sentence_no-2,0)] #-2はマジックナンバー：リクエストの時点で「ユーザーがこれまで読んだテキスト」を取得したい
    level_lst_2d=ur_data['send_level_lst'][:max(start_sentence_no-2,0)]

    wl=("|@|".join(text_lst_2d)).split("|@|")
    ll=("|@|".join(level_lst_2d)).split("|@|")
    word_lst=list(set([(x,y) for x,y in zip(wl,ll) if x!=""]))
    word_counter={'A1':0,'A2':0,'B1':0,'B2':0,'C1':0,'C2':0,'unknown':0}
    clicked_word_counter={'A1':0,'A2':0,'B1':0,'B2':0,'C1':0,'C2':0,'unknown':0}

    for word,level in word_lst:
        if level not in word_counter:
            level='unknown'
        word_counter[level]+=1

    for word,level in clicked_word_lst:
        if level not in clicked_word_counter:
            level='unknown'
        clicked_word_counter[level]+=1
    
    #clicked_word_rate={key: clicked_word_counter[key]/(word_counter[key]+1) if word_counter[key]>=5 else None for key in word_counter.keys()}
    print(clicked_word_counter)
    print(word_counter)
    #print(clicked_word_rate)

    # return https_fn.Response(json.dumps(clicked_word_rate), status=200, mimetype="application/json")

    level_to_rate = { # https://www.eiken.or.jp/cse/ を参考
        "A1":1700,
        "A2":1950,
        "B1":2300,
        "B2":2600,
        "C1":3300,
        "C2":3600,
    }
    X=[]
    Y=[]
    
    # clicked_word_counter= {'A1':1, 'A2':1,'B1':1,'B2':1,'C1':1,'C2':1,'unknown':0}
    # word_counter        = {'A1':10,'A2':10,'B1':0,'B2':0,'C1':0,'C2':0,'unknown':0}

    if sum(word_counter[level]>=10 for level in word_counter.keys())<=1:
        return now_user_rate

    logprobsum_max=-1e9
    best_rate=now_user_rate
    for rate in range(1200,3010,10):
        logprobsum=0
        for level in ['A1','A2','B1','B2','C1','C2']:
            if word_counter[level]<10:#10単語未満は信頼できないのでスキップ
                continue

            # ユーザーレートがrateだと仮定したときに、levelの単語を知らない確率
            r=probSigmoid(level_to_rate[level],rate)
            n=word_counter[level]
            k=clicked_word_counter[level]
            # n単語を確率rで知らない（クリックした）場合、知らない単語がk個となる確率
            if n<=k: #n=kはともかく、n<kはあり得ないと思うんだけどなあ
                logp=k*log(r)
            else:
                # Log(r^k * (1-r)^(n-k) * C(n,k))
                logp=k*log(r)+(n-k)*log(1-r)+sum(log(x) for x in range(n-k,n+1)) - sum(log(x) for x in range(1,k+1))

            logprobsum+=logp
        X.append(rate)
        Y.append(logprobsum)

        if logprobsum>logprobsum_max:
            logprobsum_max=logprobsum
            best_rate=rate

    print('best_rate:',best_rate)
    # plt.plot(X,Y)
    # plt.xlabel('user rate')
    # plt.ylabel('logprob sum')
    # plt.show()

    return best_rate

if __name__=="__main__":
    start_sentence_no = 8
    ur_data={'rate': 1800, 'send_text_lst': ['Alice|@|was starting|@|to feel|@|very tired|@|from sitting|@|next to|@|her sister|@|and having|@|nothing to do', "She|@|checked|@|her sister's book|@|once or twice|@|but|@|there were|@|no pictures|@|or|@|conversations", "Alice|@|wondered|@|'What|@|is|@|the point|@|of|@|a book|@|if|@|it|@|has|@|no pictures|@|or|@|talking?'", 'She|@|was thinking|@|if|@|it|@|was worth|@|getting up|@|to make|@|a daisy chain|@|as|@|the hot day|@|made her feel|@|sleepy and tired', 'Suddenly|@|a White Rabbit|@|with pink eyes|@|ran by|@|her', 'It|@|was|@|not|@|very special|@|or|@|unusual', "Alice|@|didn't find|@|it|@|strange|@|when|@|she heard|@|the Rabbit|@|say|@|'Oh dear!|@|I will be late!'|@|Later|@|she realized|@|she should have been|@|surprised|@|but|@|at that moment|@|it felt|@|normal", 'The Rabbit|@|took|@|a watch|@|out of|@|its pocket|@|looked at|@|it|@|and then|@|ran quickly|@|Alice|@|got up', 'She thought|@|she never saw|@|a rabbit|@|with a pocket|@|or a watch|@|before', 'Feeling very curious|@|she|@|quickly|@|ran across|@|the field|@|and|@|saw|@|it|@|go into|@|a big rabbit hole|@|under|@|the hedge', 'Alice|@|quickly|@|went down|@|after|@|it', "She|@|didn't think|@|about|@|how|@|she|@|would get out", "She|@|didn't think|@|about|@|how|@|she|@|would get out"], 'send_level_lst': ['A1|@|B1|@|A2|@|A2|@|A2|@|A2|@|A1|@|B1|@|A2', 'A1|@|B1|@|A1|@|A2|@|B1|@|A2|@|A2|@|A1|@|A2', 'A1|@|B1|@|B1|@|A1|@|B2|@|A1|@|A1|@|B1|@|A1|@|A1|@|A2|@|A1|@|A2', 'A1|@|B1|@|A2|@|A1|@|B2|@|A2|@|B1|@|B1|@|B2|@|A1|@|B2|@|A2', 'A2|@|A1|@|A2|@|B1|@|A1', 'A1|@|A1|@|A2|@|A2|@|A1|@|B1', 'A1|@|B2|@|A1|@|B2|@|A2|@|A2|@|A2|@|A2|@|A1|@|A2|@|A2|@|B1|@|B2|@|A2|@|A2|@|A2|@|B2|@|B2', 'A1|@|B1|@|A2|@|A2|@|A2|@|B1|@|A1|@|B1|@|B1|@|A1|@|B1', 'A2|@|A2|@|A1|@|A2|@|A2|@|B2', 'B2|@|A1|@|A2|@|B2|@|A2|@|A1|@|A2|@|B1|@|B1|@|A2|@|A1|@|A2', 'A1|@|A2|@|B1|@|A1|@|A1', 'A1|@|A2|@|B1|@|B1|@|A1|@|B1', 'A1|@|A2|@|B1|@|B1|@|A1|@|B1']}
    clicked_word_lst= [('feel','A1')]
    is_difficult_btn= False
    calcRate(start_sentence_no,ur_data,clicked_word_lst,is_difficult_btn)