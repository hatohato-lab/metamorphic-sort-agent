#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oracle.py — メタモルフィック（性質ベース）オラクル。
golden（期待出力）を持たずに、「正しい sort なら必ず満たす関係(metamorphic relation)」だけで
候補実装の正しさを判定する。テストオラクル問題への別解（正解出力が無くても検証できる）。

判定する関係（種をふった乱数入力すべてで成立せねばならない）:
  MR1 順序保存     … 出力は非減少列
  MR2 多重集合保存 … 出力は入力の並べ替え（要素と個数が一致）
  MR3 長さ保存     … len(出力)==len(入力)
  MR4 冪等         … sort(sort(x))==sort(x)
  MR5 置換不変     … 入力をシャッフルしても sort 結果は不変

加えて、エージェント産の候補には静的検査を行う: 組み込み sorted() / list.sort() の使用を
ソースから検出したら制約違反として FAIL（オラクル自身の対照ファイルは検査対象外）。

使い方:
  python oracle.py                  # reference.py（正例＝陽性対照）を採点
  python oracle.py --candidate NAME # NAME.py（エージェントの出力）を採点（.py 付きでも可）
  python oracle.py --selftest       # オラクル自身を検証（正例→PASS / 既知バグ実装→FAIL）

終了コード: 全 MR PASS（または selftest が期待どおり）で 0、それ以外 1。
"""
import argparse
import importlib.util
import io
import random
import sys
import tokenize
from collections import Counter
from pathlib import Path

# Windows コンソール(cp932)でも日本語・記号を出せるよう出力を UTF-8 に統一。
# Linux/Mac は元から UTF-8 なので無害。これが無いと Windows で print が落ちる。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

EVAL_DIR = Path(__file__).resolve().parent
CASES = EVAL_DIR / "corpus"

# 静的検査（組み込みソート禁止）の対象外ファイル。
# reference.py はオラクル自身の陽性対照（物差し）であってエージェントの解答ではないため、
# 意図的に組み込み sorted() を使っている。broken_*.py も同様にオラクル検証用の対照。
# 「自力実装」の制約はエージェント産の候補にだけ課されるので、対照は検査しない。
ORACLE_CONTROLS = {"reference.py", "broken_reverse.py", "broken_dedup.py", "broken_truncate.py"}


def find_builtin_sort(path: Path):
    """候補ソースが組み込みの sorted / .sort を使っていたら、その箇所の一覧を返す。

    tokenize ベースなのでコメント・文字列内の言及は無視する。
    候補が自分で定義する sort() の再帰呼び出し（ドットなしの sort(...)）は違反にしない。
    別名代入（s = sorted 等）によるすり抜けを防ぐため、呼び出しに限らず名前の参照自体を検出する。
    """
    src = path.read_text(encoding="utf-8")
    toks = [t for t in tokenize.generate_tokens(io.StringIO(src).readline)
            if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT,
                              tokenize.INDENT, tokenize.DEDENT)]
    hits = []
    for i, t in enumerate(toks):
        if t.type != tokenize.NAME:
            continue
        if t.string == "sorted":
            hits.append(f"{t.start[0]}行目: sorted")
        elif (t.string == "sort" and i > 0
              and toks[i - 1].type == tokenize.OP and toks[i - 1].string == "."):
            hits.append(f"{t.start[0]}行目: .sort")
    return hits


def load_sort(path: Path):
    spec = importlib.util.spec_from_file_location("cand_" + path.stem, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if not hasattr(m, "sort"):
        raise AttributeError(f"{path.name} に sort(xs) が無い")
    return m.sort


def gen_inputs(seed=0, n=200):
    rnd = random.Random(seed)
    xs = [[], [0], [1, 1, 1], [2, 1], list(range(12)), list(range(12))[::-1]]
    for _ in range(n):
        k = rnd.randint(0, 20)
        xs.append([rnd.randint(-5, 5) for _ in range(k)])  # 値域を狭め重複を多発させる
    # 長い列・広い値域のケース（長さ最大20・値域[-5,5]だけでは出ないバグを狙う）。
    # rnd は種固定なので、ここも毎回同じ列が決定的に生成される。
    for _ in range(3):
        xs.append([rnd.randint(-10**6, 10**6) for _ in range(100)])
    for _ in range(2):
        xs.append([rnd.randint(-10**6, 10**6) for _ in range(1000)])
    return xs


def is_sorted(a):
    return all(a[i] <= a[i + 1] for i in range(len(a) - 1))


def mr_order(sort, x):
    return is_sorted(sort(list(x)))


def mr_multiset(sort, x):
    return Counter(sort(list(x))) == Counter(x)


def mr_length(sort, x):
    return len(sort(list(x))) == len(x)


def mr_idempotent(sort, x):
    o = sort(list(x))
    return sort(list(o)) == o


def mr_perm_invariance(sort, x):
    o = sort(list(x))
    s = list(x)
    random.Random(12345).shuffle(s)
    return sort(s) == o


MRS = [
    ("MR1 順序保存", mr_order),
    ("MR2 多重集合保存", mr_multiset),
    ("MR3 長さ保存", mr_length),
    ("MR4 冪等", mr_idempotent),
    ("MR5 置換不変", mr_perm_invariance),
]


def evaluate(sort, inputs):
    res = {}
    for name, fn in MRS:
        passed, counter = 0, None
        for x in inputs:
            try:
                ok = fn(sort, x)
            except Exception as e:
                ok = False
                if counter is None:
                    counter = f"x={x!r} で例外 {type(e).__name__}"
            if ok:
                passed += 1
            elif counter is None:
                counter = f"反例 x={x!r}"
        res[name] = (passed, counter)
    return res


def grade(path: Path, inputs):
    if path.name not in ORACLE_CONTROLS:
        try:
            hits = find_builtin_sort(path)
        except Exception:
            hits = []  # 読めない・構文エラー等は下の load_sort が「読込失敗」として報告する
        if hits:
            detail = "制約違反（組み込みソート使用）: " + ", ".join(hits)
            return [(name, "FAIL", detail) for name, _ in MRS], False
    try:
        sort = load_sort(path)
    except Exception as e:
        return [(name, "FAIL", f"読込失敗: {e}") for name, _ in MRS], False
    res = evaluate(sort, inputs)
    rows, allpass = [], True
    for name, _ in MRS:
        passed, counter = res[name]
        ok = passed == len(inputs)
        allpass = allpass and ok
        detail = "ok" if ok else f"{passed}/{len(inputs)} … {counter}"
        rows.append((name, "PASS" if ok else "FAIL", detail))
    return rows, allpass


def print_table(rows, title):
    print(f"\n### {title}")
    print("| 関係(MR) | 判定 | 詳細 |")
    print("|---|---|---|")
    for name, verdict, detail in rows:
        print(f"| {name} | {verdict} | {detail} |")
    npass = sum(1 for _, v, _ in rows if v == "PASS")
    print(f"\n小計: {npass}/{len(rows)} MR PASS")
    return npass == len(rows)


def selftest():
    print("# オラクル自己検証 — メタモルフィック sort オラクル")
    inputs = gen_inputs()
    ref_rows, ref_ok = grade(CASES / "reference.py", inputs)
    print_table(ref_rows, "① 正しい実装 reference.py（全 MR PASS であるべき）")
    controls = [
        ("broken_reverse.py", "降順バグ → MR1 を破る"),
        ("broken_dedup.py", "重複除去バグ → MR2/MR3 を破る"),
        ("broken_truncate.py", "要素脱落バグ → MR3/MR2 を破る"),
    ]
    all_caught = True
    for fname, why in controls:
        rows, ok = grade(CASES / fname, inputs)
        caught = not ok  # バグ実装は少なくとも1つの MR で FAIL すべき
        all_caught = all_caught and caught
        print_table(rows, f"② {fname}（{why}／FAIL であるべき）→ 検出={'OK' if caught else 'NG'}")
    valid = ref_ok and all_caught
    print(f"\n## オラクル判定: {'PASS（バグを捕まえ正例を通す＝信頼できる）' if valid else 'FAIL（オラクルに欠陥）'}")
    return valid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="reference",
                    help="採点する候補ファイル名（.py は付けても付けなくてもよい）。既定=reference")
    ap.add_argument("--selftest", action="store_true", help="オラクル自身を検証")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    inputs = gen_inputs()
    name = a.candidate[:-3] if a.candidate.endswith(".py") else a.candidate
    rows, allpass = grade(CASES / f"{name}.py", inputs)
    ok = print_table(rows, f"採点: {name}.py（メタモルフィック）")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
