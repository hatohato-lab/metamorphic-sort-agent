# 陰性対照: 降順に並べるバグ。MR1（順序保存＝非減少）を破るはず。
def sort(xs):
    return sorted(xs, reverse=True)
