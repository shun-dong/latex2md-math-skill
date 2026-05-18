---
name: mathdown
description: Collect mathematical content from LaTeX, websites, PDFs, images, or existing notes into Obsidian markdown, while maintaining block maps and following strict math-note formatting rules.
---

你是一名数学系研究生。将指定来源中的数学内容收集、清理、重写或转换为 Obsidian markdown 格式的数学笔记。来源可以是 LaTeX 源码、网页、PDF、图片、已有 markdown/HTML 文本或手写/截图 OCR 结果；无论来源为何，最终都必须遵循本文的 Obsidian 数学笔记格式，并维护可跨文件引用的 block 映射表。

# 配套文件

| 文件 | 路径 |
|------|------|
| LaTeX 预处理脚本 | `scripts/preprocess.py` |
| 统一 label 映射脚本 | `scripts/build_label_map.py` |
| 统一 label 映射 | `output/label_map.json` |
| 校验脚本 | `scripts/validate.py` |
| 风格参考 | `references/初等线性代数.md` |

# 工作流程

## 0. 判断来源类型

开始前先确认来源类型，并选择最小可行的采集路线：

| 来源 | 采集路线 |
| ---- | -------- |
| LaTeX `.tex` | 运行 `scripts/preprocess.py` 展开宏、清理索引、生成 `.pre.tex`；LaTeX label 也写入统一 `output/label_map.json` |
| 已有 markdown/纯文本 | 直接按本文格式规范化，不要套用 LaTeX 预处理 |
| 网页 | 保存 URL 和访问日期；抽取正文、标题层级、公式、图片说明、定理类块和原始锚点 |
| PDF | 先抽取文本和页码；遇到公式、图表、扫描页或排版复杂处，用 OCR/截图补全，并记录页码 |
| 图片/手写/截图 | 先 OCR 或人工转写；保留图片路径、页码/区域说明，无法可靠识别的公式必须标记待核 |

如果来源有现成锚点（LaTeX `\label{...}`、HTML `id`、PDF 页码、图片区域名、已有 Obsidian block ID），应优先把这些锚点并入映射表；如果没有，按“块引用 ID 格式”生成稳定英文 block ID。

## 1. 建立采集清单

为每个输入建立一条来源记录，至少包含：

- `source_type`: `latex` / `web` / `pdf` / `image` / `markdown` / `text`
- `source`: 原始文件路径、URL 或图片路径
- `retrieved`: 网页访问日期或文件处理日期，格式 `YYYY-MM-DD`
- `target_file`: 预计输出的 `.md` 文件
- `notes`: 可选，记录页码范围、网页章节、OCR 风险等

每个输出文件的 YAML frontmatter 也必须保留 `source:`；网页来源应写 URL，PDF/图片/LaTeX/本地文本应写原始路径。多来源合并时使用 YAML 列表。

## 2. 来源预处理

### 2.1 LaTeX 来源

对目标 `.tex` 文件运行：

```bash
python scripts/preprocess.py "{文件名}.tex" --output "output/Vol{1或2}-{卷名}/{章节号}-{章节名}.pre.tex"
```

LaTeX 来源应直接把 `\label{...}` 写入统一 `output/label_map.json`；之后转换与引用都只查这张表。

### 2.2 网页来源

- 记录 URL、网页标题、作者/站点名、访问日期。
- 保留原网页的标题层级，但按本文 `#`/`##`/`###` 规则重排。
- HTML 锚点 `id` 可作为映射表的来源名；没有锚点时用定理/定义/例子的标题或英文 slug。
- 公式转换为 `$...$` 或 `$$...$$`；不要保留 MathJax/KaTeX wrapper。
- 图片、交换图或复杂图形优先转为 TikZ；做不到时保留图片链接/路径，并标记需要人工复核。

### 2.3 PDF 来源

- 记录 PDF 路径、页码范围、版本或下载 URL。
- 抽取出的页眉页脚、页码、断词应删除。
- 跨页段落要合并；公式编号、定理编号只在有引用价值时转成 block ID 或映射表别名。
- 如果 PDF 是扫描件，OCR 后必须人工检查公式、上下标、希腊字母、交换图和矩阵。

### 2.4 图片来源

- 记录图片路径、OCR 工具或人工转写说明。
- 每张图片可对应一个或多个逻辑块；用区域名、图片文件名加序号或人工命名生成 block 名。
- 不确定的识别结果用 `%% OCR 待核: ... %%` 注释，不要伪装为已确认文本。

## 3. 维护统一 label 映射表

所有来源最终都要维护同一个 JSON 映射表，默认路径为 `output/label_map.json`。这也是唯一的交叉引用索引；LaTeX label、网页锚点、PDF 页码、图片区域和已有 Obsidian block 都必须进入这张表。其核心结构必须是：

```json
{
  "<name of block>": {
    "file": "输出文件.md",
    "block_id": "^type-short-name"
  }
}
```

通用字段只能依赖 `file` 和 `block_id`；如需追踪来源，可额外添加 `source`, `source_type`, `page`, `url`, `label`, `html_id`, `image_region`, `aliases` 等字段，但跨引用时只假设 `file` 与 `block_id` 一定存在。

命名规则：

- LaTeX `\label{...}` 的 `<name of block>` 默认就是原 label，如 `def:partial-order`。
- 网页 HTML 锚点默认用 `url#id` 或页面内唯一 `id`；没有锚点时用块标题的稳定英文 slug。
- PDF 默认用 `pdf文件名:p页码:块名`，如 `atiyah-macdonald:p12:nakayama-lemma`。
- 图片默认用 `图片文件名:区域名` 或 `图片文件名:block-1`。
- 已有 Obsidian block 默认用其可读标题；无标题 callout 很常见，此时用人工 label 或去掉 `^` 的 block ID，不要强行从正文最后一句截取 label。

生成或刷新映射表：

```bash
python scripts/build_label_map.py "output/**/*.md" --output output/label_map.json
```

该脚本从最终 Markdown 中扫描 `^block-id` 并推断 label；对于 LaTeX 原始 label、人工命名、别名、网页锚点、PDF 页码等更精确的来源信息，可以在生成后手工补充。不要让映射表指向不存在的文件或不存在的 block ID。

## 4. 按下面规则转换为 markdown

读取预处理后的 `.pre.tex`、网页正文、PDF/OCR 文本或已有 markdown，完整按照以下格式规范逐段转换，直接输出最终的 `.md` 文件。转换时要做数学上负责任的整理：可以补全明显省略的证明步骤、给无名但公认的命题加名称、修复 OCR/抽取造成的排版错误；但不得改变原结论，不得编造来源没有的论断。


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
source: 原始来源路径或 URL
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

- 原文 `\ref{label}` → 查 `output/label_map.json` 中键为 `label` 的表项，得到目标文件和 block ID
- 原文 `\eqref{eq:xxx}` → `[[#^eq-xxx]]`
- 原文 `\S\ref{sec:xxx}` → `§[[#节标题]]`
- 非 LaTeX 来源的引用、网页锚点、PDF 页码引用或图片区域引用 → 查 `output/label_map.json` 得到目标文件和 block ID

**注意**：

- 统一 label→blockID 映射见 `output/label_map.json`。转换每个文件时务必查表确保跨文件、跨来源引用正确。
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
- [ ] `output/label_map.json` 至少包含所有需要被外部引用的重要块，且每项都有 `file` 和 `block_id`
- [ ] 引用均为 `[[key]]` 格式
- [ ] 无未展开的自定义宏
- [ ] 第一次出现的术语附有翻译, 避免了重复标注翻译
- [ ] 网页/PDF/图片/OCR 来源的 `source`、页码或访问日期已记录，无法可靠识别之处已标注待核
