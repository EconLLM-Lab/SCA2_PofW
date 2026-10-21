# WB7-R: Data-rights ruling for the public workbench (2026-10-21)

Scope: the public Hugging Face Space `EconLLM/sca2-workbench` (https://huggingface.co/spaces/EconLLM/sca2-workbench),
static site, public since 2026-10-20, run by an Arizona State University research group, no commercial use.
Method: public sources only, read 2026-10-21 (MST). Nothing under `data/` and no respondent-level file was opened.
The GPS live site could not be reached from this environment; its download-agreement page is quoted from the
Internet Archive capture of 2025-11-12 (URL below), which matches the site's current structure. Rulings are
evidence from the public terms, not authorization: the PM carries them to Augusto, and Augusto confirms in writing
before the human layer ships (per WB7-0).

## Summary table

| # | Item | Ruling | Governing sentence (source URL below) | Required action |
|---|---|---|---|---|
| 1 | WVS wave 7 question wording and answer labels (Q43, Q50, Q57, Q81, Q99, Q106, Q176) | **permitted with attribution** | The conditions attach to the "data files", not the questionnaire: "These data files are available without restrictions, provided: a) that they are used for non-profit purposes; b) correct citations are provided and sent to the World Values Survey Association …; c) the data files themselves are not redistributed; d) proper citation … is included into the references list of the publication." The WVS-7 questionnaire itself is public documentation, downloadable without registration. | Label each shipped question with the WVS-7 questionnaire as source; carry the WVS-7 citation line (below). |
| 2 | Binary GPS signs (42 countries x 6 preferences, above/below reference; no GPS values) | **permitted with attribution** | "This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. The following two papers have to be cited in all publications that make use of or refer in any kind to the files provided: Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D., & Sunde, U. (2018). Global evidence on economic preferences … [and] Falk … (2016). The preference survey module … IZA DP No. 9674." | Carry both GPS citation lines and the CC BY-NC-SA 4.0 notice on the shipped sign table (below); send the paper link to the GPS team; ship no GPS magnitudes (already true). |
| 3 | Country-level WVS-7 aggregates (weighted share per answer, whole percent, with n; no microdata) | **permitted with attribution** | Same WVS conditions; the rule that separates statistics from redistribution is "the data files themselves are not redistributed" — statistics derived from the files are "results", governed by the citation rule ("… for each publication of results based in part or entirely on these data files"). WVS itself publishes such aggregates openly in its Online Data Analysis tool, no login. | Carry the WVS-7 citation line on the Space; email the citation and a Space link to the WVSA Secretariat (wvsa.secretariat@gmail.com). |
| 4 | Model outputs of Llama-3.1-8B-Instruct and its LoRA adapters (probabilities, activations; no weights) | **permitted with attribution** | "If you distribute or make available the Llama Materials (or any derivative works thereof), or a product or service (including another AI model) that contains any of them, you shall … (B) prominently display 'Built with Llama' on a related website, user interface, blogpost, about page, or product documentation." Outputs are not restricted; the naming clause triggers only if outputs are used to train a distributed model (not the case: adapters are trained on GPS signs). | Add "Built with Llama" prominently (landing page and README) with the license notice line. **Not currently met on the live Space** (checked: README, root index.html, story page, JS bundle — zero occurrences). |

## Detail and governing quotes

### 1. WVS wave 7 question wording and answer labels — permitted with attribution

- Conditions of Use at download (registration form shown before the W7 data download),
  https://www.worldvaluessurvey.org/AJDownloadLicense.jsp :
  "These data files are available without restrictions, provided: a) that they are used for non-profit purposes;
  b) correct citations are provided and sent to the World Values Survey Association for each publication of
  results based in part or entirely on these data files; c) the data files themselves are not redistributed;
  d) proper citation to the WVS data is included into the references list of the publication."
- What ships here is questionnaire wording and answer labels, not a data file. The WVS-7 questionnaires and
  codebooks are public on the documentation page, no registration:
  https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp
- The same wording and labels are displayed openly, without login, in WVS's own Online Data Analysis tool:
  https://www.worldvaluessurvey.org/WVSOnline.jsp
- Nothing in the public terms restricts reproducing question wording; the obligations (citation, no
  redistribution of data files, non-profit) attach to the data files. The workbench quotes ~7 items verbatim
  with a source label — standard scholarly quotation of public documentation.
- Required action: each shipped question carries "World Values Survey, Wave 7 questionnaire (2017–2022),
  worldvaluessurvey.org" as its source, and the WVS-7 citation line (below) is on the Space.

### 2. Binary signs derived from the Global Preferences Survey — permitted with attribution

- GPS downloads page, citation agreement (Internet Archive capture 2025-11-12 of
  https://gps.econ.uni-bonn.de/downloads ,
  https://web.archive.org/web/20251112102824/https://gps.econ.uni-bonn.de/downloads ):
  "Our data can be accessed for further research. Please select the relevant datasets, questionnaires or
  supplementary material and accept the citation agreement. Please note that these data must not be
  transferred to third parties without prior approval." — "These data" are the downloadable data files
  (country-level and individual-level datasets). The shipped signs are not those files and carry no GPS value.
- Same page: "This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0
  International License. The following two papers have to be cited in all publications that make use of or
  refer in any kind to the files provided: [Falk et al. 2018 QJE; Falk et al. 2016 IZA DP 9674]" and
  "We also kindly ask researchers using the GPS data or the preference module to send us their paper, or a
  link to their paper."
- The GPS project itself publishes country-level comparisons openly, without registration: its rankings and
  maps pages (https://gps.econ.uni-bonn.de/rankings , /maps) and the interactive country tool. A one-bit
  above/below indicator per (country, preference) is strictly less information than the open rankings.
- The country-level dataset is CC BY-NC-SA 4.0; a binary table derived from it is an adaptation under that
  license, so the shipped sign table carries the same license notice and attribution. The workbench site is
  non-commercial (ASU research group, no commercial use), which satisfies the NC term.
- Required action: the two citation lines (below) on the Space, near the signs or in a sources section;
  the sign table marked "derived from GPS country-level data, CC BY-NC-SA 4.0"; the Paper B link sent to
  the GPS team (its contact page) per their request. No GPS magnitudes ship (already true and verified).

### 3. Country-level WVS-7 aggregates — permitted with attribution (this gates WB7-H)

- Same Conditions of Use as item 1: https://www.worldvaluessurvey.org/AJDownloadLicense.jsp .
  The redistribution clause is explicit that it is the data files, not statistics:
  "the data files themselves are not redistributed". Statistics computed from the files are "results",
  and results are governed by the citation clause: "correct citations are provided and sent to the World
  Values Survey Association for each publication of results based in part or entirely on these data files".
- The Timeseries conditions page repeats the same three restrictions:
  https://www.worldvaluessurvey.org/WVSContents.jsp?CMSID=intconduse
  ("They are used for non-profit purposes; Data files are not redistributed; Correct citations are provided
  wherever results based on the data are published").
- Comparison with what the WVS Association itself publishes openly: its Online Data Analysis tool
  (https://www.worldvaluessurvey.org/WVSOnline.jsp , "Welcome to the World Values Survey Data analysis tool.
  To view data from a wave, click on the wave period", 2017-2022 selectable) shows weighted cross-tabulations
  openly, with no login; the WVS-7 documentation page publishes per-country codebooks with n and sampling
  detail. A rounded, whole-percent weighted share per (country, question, answer) with n is the same class
  of statistic, at lower resolution than the tool shows.
- Non-profit purpose: satisfied (ASU research group, public research workbench, no commercial use).
- No microdata and no respondent row ships: satisfied by the WB7 plan gate ("at most one country-level
  aggregate per (country, question, answer), rounded to whole percent, with n and the WVS-7 source").
- Required action: WVS-7 citation line on the Space, and the citation plus a link to the Space sent to the
  WVSA Secretariat (wvsa.secretariat@gmail.com). If Augusto or the ASU data steward prefers written
  confirmation that a public web tool counts as a "publication", the WVSA Secretariat decides; my reading
  of the public terms is that it does.

### 4. Llama-3.1-8B-Instruct outputs and LoRA-adapter outputs — permitted with attribution

- Llama 3.1 Community License Agreement, full text (Meta's official mirror):
  https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/LICENSE
  (view: https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE ).
- Outputs. The license defines "Llama Materials" as Meta's models, weights and Documentation. The license
  nowhere restricts use of outputs; the only output-related clause is the naming clause: "If you use the
  Llama Materials or any outputs or results of the Llama Materials to create, train, fine tune, or otherwise
  improve an AI model, which is distributed or made available, you shall also include 'Llama' at the beginning
  of any such AI model name." The adapters are trained on GPS signs, not on Llama outputs, so this clause is
  not triggered by the current pipeline; and the adapters themselves are not distributed (no weights ship on
  the Space).
- Attribution. Section 1.b.i: "If you distribute or make available the Llama Materials (or any derivative
  works thereof), or a product or service (including another AI model) that contains any of them, you shall
  (A) provide a copy of this Agreement with any such Llama Materials; and (B) prominently display 'Built with
  Llama' on a related website, user interface, blogpost, about page, or product documentation."
  Strict reading: an outputs-only site triggers none of it. Conservative reading: a public site whose entire
  content is outputs of Llama 3.1 and of derivative-work adapters, and which brands itself "inside
  Llama-3.1-8B", is a "related website"/product presenting derivative-work outputs, so 1.b.i(B) applies.
  The ruling follows the conservative reading: the display is required, and it costs one line.
- Current compliance of the live Space — **not met**. Checked 2026-10-21 on the live pages:
  - Space README (https://huggingface.co/spaces/EconLLM/sca2-workbench/raw/main/README.md): no
    "Built with Llama", no license notice.
  - Landing page (https://huggingface.co/spaces/EconLLM/sca2-workbench/raw/main/index.html): names
    Llama-3.1-8B-Instruct in title/description; no "Built with Llama".
  - Story page (https://econllm-sca2-workbench.static.hf.space/sca2/index.html): no "Built with Llama"
    (grep of the full page text).
  - Workbench JS bundle (assets/index-CCjLwD0I.js, 715,679 bytes): `grep -c "Built with"` = 0 occurrences;
    "World Values Survey" and "Global Preferences Survey" appear without any citation.
- Naming note: the internal adapter identifiers (e.g. `llama31_8b_nf4_dequant_..._bgd`) begin with
  "llama31", not "Llama". This is moot while adapters are not distributed; if adapters ever ship publicly,
  1.b.i's naming sentence requires "Llama" at the beginning of the model name plus a license copy.
- Section 1.b.iii (retain the Notice text in distributed copies of Llama Materials) applies only to copies of
  the materials themselves — not triggered by an outputs-only site; the notice line is included below anyway.

## Attribution and citation lines the Space must carry

WVS (on any page that shows WVS question wording or WVS-derived figures):

> Haerpfer, C., Inglehart, R., Moreno, A., Welzel, C., Kizilova, K., Diez-Medrano J., M. Lagos, P. Norris,
> E. Ponarin & B. Puranen et al. (eds.). 2020. World Values Survey: Round Seven – Country-Pooled Datafile.
> Madrid, Spain & Vienna, Austria: JD Systems Institute & WVSA Secretariat. doi.org/10.14281/18241.1
> Source: World Values Survey Wave 7 (2017–2022), worldvaluessurvey.org
> (citation format per https://www.worldvaluessurvey.org/WVSEventsShow.jsp?ID=362 )

and, per the Conditions of Use, the same citation must be sent to wvsa.secretariat@gmail.com for the
"publication" that is the public Space (include the Space URL).

GPS (on any page that shows the preference signs):

> Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D., & Sunde, U. (2018). Global evidence on economic
> preferences. Quarterly Journal of Economics, 133(4), 1645–1692.
> Falk, A., Becker, A., Dohmen, T. J., Huffman, D., & Sunde, U. (2016). The preference survey module: A
> validated instrument for measuring risk, time, and social preferences. IZA Discussion Paper No. 9674.
> Preference signs derived from Global Preferences Survey country-level data (gps.econ.uni-bonn.de),
> licensed CC BY-NC-SA 4.0. No GPS values are shipped.

Llama (landing page and README, prominent):

> Built with Llama
> Llama 3.1 is licensed under the Llama 3.1 Community License, Copyright © Meta Platforms, Inc. All Rights
> Reserved. (https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE)

## Item 3 overall verdict (gates WB7-H)

**Country-level WVS-7 weighted aggregates are permitted with attribution: they may ship on the public Space
with the WVS-7 citation displayed and sent to the WVSA Secretariat; no WVS data file or respondent row ships.**

## Residual notes (who decides what is left)

- The WVSA reading here is that a public web tool is a "publication of results" under the Conditions of Use.
  If Augusto or the ASU data steward wants that confirmed rather than read, the WVSA Secretariat
  (wvsa.secretariat@gmail.com) decides; the question is one email.
- The GPS downloads page was quoted from the Internet Archive capture of 2025-11-12 because the live
  gps.econ.uni-bonn.de subpages were unreachable from this environment (the GPS home page was read live).
  The PM should spot-check the live downloads page once (one glance: license line and the two citations).
- Decisions that belong to Augusto (whether the human layer ships at all, and his written confirmation of
  this ruling) are not made here; this document is the rights evidence for that decision.

## Sources read (public, 2026-10-21 MST)

- https://www.worldvaluessurvey.org/AJDownloadLicense.jsp (WVS download Conditions of Use)
- https://www.worldvaluessurvey.org/WVSContents.jsp?CMSID=intconduse (EVS/WVS timeseries conditions)
- https://www.worldvaluessurvey.org/WVSEventsShow.jsp?ID=362 (WVS citation rules, WVS-7 citation format)
- https://www.worldvaluessurvey.org/WVSOnline.jsp (WVS open online analysis tool)
- https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp (WVS-7 questionnaires and codebooks, public)
- https://gps.econ.uni-bonn.de/ (GPS home, live)
- https://web.archive.org/web/20251112102824/https://gps.econ.uni-bonn.de/downloads (GPS downloads and
  citation agreement; archive capture)
- https://web.archive.org/web/20251112114246/https://gps.econ.uni-bonn.de/faq (GPS FAQ, archive capture)
- https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/LICENSE (Llama 3.1
  Community License, Meta's official mirror)
- Live Space: README, index.html, story page, JS bundle, HF tree API (compliance check, item 4)
