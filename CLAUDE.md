# CLAUDE.md — metamorphic-sort-agent

このリポジトリは「整数リストを手書きアルゴリズムで昇順ソートする」エージェントと、その採点係（メタモルフィック）です。
正解表を持たず、「正しいソートなら必ず成り立つ性質（順序・要素保存・冪等・置換不変・長さ保存）」で判定します。

## 確認のしかた

- `python eval/oracle.py --selftest` … 採点係が正しいか（正例=PASS／既知バグ=FAIL）
- `python eval/oracle.py --candidate candidate` … エージェントの答え（`eval/corpus/candidate.py`）を採点
- `python eval/oracle.py` … お手本(reference.py)を採点

## いじるときの約束（評価駆動 / EDD）

- 先に eval（合否の基準）を満たすことを確認してから「完成」とする。雰囲気で done にしない。
- `eval/corpus/reference.py` と `broken_*.py` は採点係の検証用。むやみに変えない。
- Python 標準ライブラリのみ。秘密情報・個人情報・客先コードを入れない。

## ファイルの役割

- `.claude/agents/metamorphic-sort-agent.md` … エージェント定義
- `eval/oracle.py` … 採点係（メタモルフィック）／`design/design.md` … 設計／`README.md` … 説明
