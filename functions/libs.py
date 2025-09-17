def getWeight(rate, level_to_rate):
    # レート順にソート
    levels = sorted(level_to_rate.items(), key=lambda x: x[1])
    
    # 範囲を探す
    for i in range(len(levels) - 1):
        l1, r1 = levels[i]
        l2, r2 = levels[i+1]
        if r1 <= rate <= r2:
            # 内分比を計算 (l1 : l2)
            w2 = rate - r1
            w1 = r2 - rate
            weights = {l1: w1, l2: w2}
            break
    else:
        # 範囲外 → 一番近いレベルを100%選ぶ
        closest = min(levels, key=lambda x: abs(x[1] - rate))[0]
        weights = {closest: 1}
    
    # 重みに基づいて選択
    choices, w = zip(*weights.items())
    return choices,w

def MultiSplit(s,seps):
    result=[]
    
    start=0
    for i in range(len(s)):
        if s[i] in seps:
            if start!=i:#2連続でsepが来た場合、空文字は入れずに飛ばす
                result.append(s[start:i])
            start=i+1
            
    
    result.append(s[start:])
    return result

if __name__=="__main__":
    level_to_rate = { # https://www.eiken.or.jp/cse/ を参考
        "A1":1500,
        "A2":1800,
        "B1":2100,
        "B2":2400,
        "ORIGINAL":2700,
    }
    rate=800
    choices,weights=getWeight(rate, level_to_rate)
    print(choices,weights)