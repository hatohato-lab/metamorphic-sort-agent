# 陰性対照: 最小要素を1つ落とすバグ。MR3（長さ保存）/ MR2（多重集合保存）を破るはず。
def sort(xs):
    r = sorted(xs)
    return r[1:]
