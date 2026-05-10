---
name: latex2md-math
description: Convert LaTeX source files to Obsidian markdown format for mathematical notes, following specific formatting rules and conventions.
---

你是一名数学系研究生。将指定 LaTeX 源码转换为 Obsidian markdown 格式的数学笔记。

# 配套文件

| 文件 | 路径 |
|------|------|
| 预处理脚本 | `scripts/preprocess.py` |
| 全局 label 映射 | `output/label_map.json` |
| 校验脚本 | `scripts/validate.py` |
| 风格参考 | `references/初等线性代数.md` |

# 工作流程

## 1. 预处理

对目标 `.tex` 文件运行：

```bash
python scripts/preprocess.py "{文件名}.tex" --output "output/Vol{1或2}-{卷名}/{章节号}-{章节名}.pre.tex"
```

## 2. 查 label 映射

读取 `output/label_map.json`，提取本章所有 `\label{...}` 对应的 block ID，以及本章 `\ref{...}` 引用的外部 label 对应的文件和 block ID。

## 3. 按下面规则转换为 markdown

读取预处理后的 `.pre.tex`，完整按照以下格式规范逐段转换，直接输出最终的 `.md` 文件。


# 笔记格式规范

## 基本规则

1. 公式使用 LaTeX 格式：行内 `$...$`，独立 `$$...$$`，`$` 和公式间不要有空格
2. 数学图使用 TikZ，放在 ` ```tikz ` 代码块中
3. 整体保持简洁紧凑，不要添加不必要的空行和分割线
4. 保留原始语言（文言白话一如原文），**不添加原文没有的额外内容**
5. 不要输出任何闲聊，直接输出数学讲义风格的 Markdown

## 文件结构

每章一个 `.md` 文件，以 YAML frontmatter 开头：

```yaml
---
aliases:
  - English Title
tags:
  - {resource}
created: YYYY-MM-DD
source: 原始tex文件路径
---
```

## 层级标题

- `#` 章标题 (对应 `\chapter`)
- `##` 节标题 (对应 `\section`)
- `###` 小节标题 (对应 `\subsection`)
- `####` 次小节标题 (对应 `\subsubsection`)

`\part*{...}` 转为 `##` 级标题。

## Callout 块（定理类环境）

### 允许的类型

仅允许以下 callout 类型（全部小写，不带数字序号）：

| Callout 类型       | 对应 LaTeX 环境     | 说明          |
| ------------------ | ------------------- | ------------- |
| `> [!definition]`         | definition          | 定义          |
| `> [!theorem]`         | theorem             | 定理          |
| `> [!lemma]`       | lemma               | 引理          |
| `> [!proposition]` | proposition         | 命题          |
| `> [!corollary]`         | corollary           | 推论          |
| `> [!claim]`       | claim               | 断言          |
| `> [!axiom]`       | axiom               | 公理          |
| `> [!remark]`      | remark, wenxintishi | 注记/温馨体示 |
| `> [!example]`         | example             | 例子          |
| `> [!exercise]`    | exercise            | 例题          |
| `> [!hypothesis]`  | hypothesis          | 假设          |
| `> [!conjecture]`  | conjecture          | 猜想          |

**注意**：

- `wenxintishi` → `> [!remark]`（不是 `[!wenxintishi]`）
- `convention` → `> [!remark]`
- `hint` → 习题后的 `*Hint.* ...` 斜体段落
- 原文无名字的命题，如有公认俗名（如蝴蝶引理、第一同构定理）应加上，否则不加，**严禁编造**

### 块引用 ID 格式

Block ID 放在 callout 块的**外面**，用空行隔开：

```markdown
> [!definition] 宇宙
> 本书所谓的*宇宙*, 意谓一个满足下述性质的集合 $\mathcal{U}$.
> **U.1** $u \in \mathcal{U} \implies u \subset \mathcal{U}$...
>
> 对于集合 $X$, 若 $X \in \mathcal{U}$ 则称为 $\mathcal{U}$-集...

^def-universe

随后正文继续...
```

规则：

- Block ID 中只能出现数字, 字母, 连字符
- Block ID 独占一行，前后各空一行
- 命名：`^` + 类型前缀 + `-` + 简短英文标识
  - 类型前缀：`definition`, `theorem`, `lemma`, `proposition`, `corollary`, `claim`, `axiom`, `remark`, `example`, `exercise`, `hypothesis`, `conjecture`
  - 示例：`^def-universe`、`^thm-zorn`、`^prop-ordinal-ordertype`
- 如果一个块有多个段落，block ID 放在最后一个段落之后

### Callout 内容格式

- callout 块内的内容每行以 `>` 开头（包括空行也要写 `>`）
- 块内的 `$$...$$` 公式每行也加 `>` 前缀
- 块内的 TikZ 代码块每行也加 `>` 前缀（参照 `初等线性代数.md`）
- **仅仅**定理/定义等放在块中。证明和解释直接写，前面**不要**加 `>` 符号

## 证明格式

证明写在 callout 块**外面**：

```
$Proof.$ 证明内容...

中间可以有多个段落。

$\blacksquare$
```

- 以 `$Proof.$` 开头
- 以 `$\blacksquare$` 结尾
- 证明内可以包含 `$$...$$` 公式，正常写即可
- 证明可以适当展开：补全跳过的中间步骤，将"显然"、"易知"替换为实际推理
- 但不得改变证明的逻辑结构，不得添加原文没有的结论

## 交叉引用

使用 Obsidian 块引用语法：

| 情况           | 格式                  |
| -------------- | --------------------- |
| 同文件引用定理 | `[[#^thm-zorn]]`      |
| 跨文件引用定义 | `[[群论#^def-group]]` |
| 引用节/小节    | `[[#序结构与序数]]`   |
| 跨文件引用节   | `[[群论#Sylow 定理]]` |

- 原文 `\ref{label}` → 查 `label_map.json` 得到目标文件和 block ID
- 原文 `\eqref{eq:xxx}` → `[[#^eq-xxx]]`
- 原文 `\S\ref{sec:xxx}` → `§[[#节标题]]`

**注意**：

- 全局 label→blockID 映射见 `output/label_map.json`。转换每章时务必查表确保跨章引用正确。
- 不要在公式块中使用 \tag 语法, 而应该在公式后紧跟 `^{id}` 和一个空行, 例如

```markdown
$$
E=mc^2
$$
^eq-einstein

接下来的内容...
```

## 引用文献

使用 Obsidian wiki 链接格式：

| 格式                  | 示例                 |
| --------------------- | -------------------- |
| `\cite{key}`          | `[[key]]`            |
| `\cite[p.52]{key}`    | `[[key]], p.52`      |
| `\cite[第 2 章]{key}` | `[[key]], 第 2 章`   |
| `\cite{key1,key2}`    | `[[key1]]; [[key2]]` |

## 列表

| LaTeX 环境                    | Markdown 输出                                                |
| ----------------------------- | ------------------------------------------------------------ |
| `compactitem` / `itemize`     | `- item` (无序列表)                                          |
| `compactenum` / `enumerate`   | `1. item` (有序列表)                                         |
| `compactdesc` / `description` | `- **label**: content`                                       |
| `inparaenum`                  | 不引起歧义时直接用有序列表，否则用 `(i) ..., (ii) ...` (行内枚举) |

## 文本格式

| LaTeX          | Markdown       |
| -------------- | -------------- |
| `\emph{...}`   | `*...*`        |
| `\textbf{...}` | `**...**`      |
| `\textit{...}` | `*...*`        |
| `\texttt{...}` | `` `...` ``    |
| `\textsf{...}` | 保持原样或去掉 |
| `\heiti{...}`  | `**...**`      |

## 特殊元素

| LaTeX              | 处理            |
| ------------------ | --------------- |
| `\index{...}`      | 删除            |
| `\mycomm{...}`     | `%% ... %%`     |
| `\footnote{...}`   | `[^n]` 文末汇总 |
| `\url{...}`        | `<...>`         |
| `\href{url}{text}` | `[text](url)`   |
| `\dag` / `\ddag`   | `†` / `‡`       |

## 习题

章末习题转为有序列表，`hint` 环境转为 `*Hint.* ...`：

```markdown
## 习题

1. 题目内容...
   *Hint.* 提示内容...

2. 题目内容...
```

## TikZ 图

- 放在 ` ```tikz ` 代码块中, 而 **不是** 公式中
- 如果在 callout 块内，每行加 `> ` 前缀
- 保留原始的 `\usepackage{tikz-cd}` 等前置声明

例子

```markdown
```tikz
\usepackage{tikz-cd}
\begin{document}
\begin{tikzcd}
V\arrow[r, "T"]\arrow[rd, "T^*g=g\circ T"']& W\arrow[d, "g"]\\
& K
\end{tikzcd}
\end{document}
```
```

如果已经在块环境中则要保证首尾有块的前缀, 比如

```markdown
> [!def] 转置(transpose)
>对于 $T: V \to W$, 定义 $T^*:W^*\to V^* := g \mapsto g\circ T$
>```tikz
\usepackage{tikz-cd}\begin{document}\begin{tikzcd}
V\arrow[r, "T"]\arrow[rd, "T^*g=g\circ T"']& W\arrow[d, "g"]\\
& K
\end{tikzcd}\end{document}
> ```
```



## 术语翻译

数学术语在文中须被翻译为中文, 并且不要使用外文简写 (例如不要将 “主理想整环” 写成 “PID”), 除非术语由人名构成导致过于冗长 (例如 ZFC 集合论、BRST 量子化等). 在一个文件第一次出现的翻译术语后面标注其外文原文 (如“整环 (integer domain, domain)”).
 如果提及数学书, 应首先给出此书在源语言中的名称, 再给出此书的中文译名. 如果行文中再次出现同一本书, 为了行文的流畅性, 应仅写出书籍的中文译名.

很多数学概念、数学定理都以人名命名. 如果该人名是中文, 则应将它写成汉字. 若不是, 则应采用通用的拉丁字母拼写. 如果原语言中有扩充的拉丁字母 (如 ß, þ, ð), 或有字母上的音符 (é, è, ê) 应保留之. 例如: 陈类、Lie 代数、Nakayama 引理、Gauß 绝妙定理、Calabi–丘流形, Euclid 几何, Pontryagin 对偶, Poincaré 群.

如在西文中, 人名在数学概念中加以后缀, 翻译后须去掉后缀, 转化为人名本身. 例如: Abel 群, Abel 化, Descartes 积, Riemann 几何.

不过, 如果出现外文的国名和地名, 仍应采用通用的中文译名.

## 格式检查清单

转换后应检查：

- [ ] 所有 `$` 和 `$$` 正确配对
- [ ] Callout 块正确闭合（`> ` 前缀一致）
- [ ] Block ID 格式正确（块外、空行隔开）
- [ ] 无 `\begin{...}` / `\end{...}` 残留
- [ ] 交叉引用指向有效的 block ID
- [ ] 引用均为 `[[key]]` 格式
- [ ] 无未展开的自定义宏
- [ ] 第一次出现的术语附有翻译, 避免了重复标注翻译