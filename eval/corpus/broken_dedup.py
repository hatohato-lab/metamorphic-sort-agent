# 陰性対照: 重複を落としてしまうバグ。MR2（多重集合保存）/ MR3（長さ保存）を破るはず。
def sort(xs):
    return sorted(set(xs))
