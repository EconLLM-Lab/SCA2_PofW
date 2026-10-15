#!/usr/bin/env python3
"""Build the Paper A item measurement table from repo sources already extracted.

Does not modify the SCA2 repo. Ranges are computed here, not typed by hand.
"""
from __future__ import annotations

import csv
from pathlib import Path

OUT = Path("/Users/bonorinoa/Hermes/Projects/SCA2/pre_arxiv_checks/item_table")

# Valid non-missing codes are the questionnaire response codes. Missing-code
# inventories differ across sources; that disagreement is recorded in the notes,
# not resolved here.
SCALE_1_4 = [1, 2, 3, 4]
SCALE_1_10 = list(range(1, 11))
SCALE_1_3 = [1, 2, 3]
MEMBER = [0, 1, 2]
BINARY = [1, 2]


def g_values(codes: list[int], kind: str) -> list[float]:
    out = []
    for v in codes:
        s = float(v)
        if kind == "binary":
            out.append(1.0 if s == 1.0 else 0.0)
        elif kind == "inv4":
            out.append(5.0 - s)
        elif kind == "inv10":
            out.append(11.0 - s)
        elif kind == "raw":
            out.append(s)
        else:
            raise ValueError(kind)
    return out


def rng(codes: list[int], kind: str) -> tuple[float, float]:
    vals = g_values(codes, kind)
    return min(vals), max(vals)


# kind is the script/tex map for retained items. Q69-Q71 use kind "inv4" only
# as the script map; tex silence is recorded in recode_g.
ROWS = [
    {
        "wvs_id": "Q57",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": BINARY,
        "kind": "binary",
        "wording": "Most people can be trusted (1) vs need to be very careful (2)",
        "wording_source": "data/WVS/MasterQuestionnaire.pdf (Q57); corroborated by DPO_eval_WVS/question_map_wvs_edited.csv and WVS_wave7.dta variable label 'Most people can be trusted'",
        "valid_responses": "1=Most people can be trusted; 2=Need to be very careful",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta value labels and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means code 1, 'Most people can be trusted', rather than code 2, 'Need to be very careful'. Derived from g(v)=1{v=1} and those labels. The paper does not separately state the direction of the recoded score.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper (results.tex tab:map): trust row, 'Generalized, interpersonal, and institutional trust/confidence'. Item-level (results.tex): 'Q57 is the generalized-trust item related to the GPS validation comparison' (Falk et al. 2018). Config (data/merged/CONSTRUCT_MAP.md): Falk et al. 2018 Table II, this exact item vs GPS trust.",
        "status": "not designated in source",
        "status_note": "Paper does not use 'primary/direct'. It distinguishes Q57 as the generalized-trust item related to the GPS validation comparison, and it does not call this item an exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q58",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Trust: your family (1 trust completely … 4 do not trust at all)",
        "wording_source": "MasterQuestionnaire.pdf Q58 object 'Your family' under the trust-groups stem; WVS_wave7.dta variable label 'Trust: Your family'",
        "valid_responses": "1=Trust completely; 2=Trust somewhat; 3=Do not trust very much; 4=Do not trust at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more trust, toward raw 1 'Trust completely' and away from raw 4 'Do not trust at all'. Derived from g(v)=5-v and those labels. Config comment (analysis/phase2/06_construct_bridge.py): trust 1-4, higher raw = less trust, so 5-raw.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source, beyond 'The wider trust composite pools substantively different items.' Config (CONSTRUCT_MAP.md / WVS_ITEM_MAP): 'Trust: Family (1-4 inv, in-group)'; Q58-Q63 described as the radius-of-trust battery.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q59",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Trust: your neighborhood (1 trust completely … 4 do not trust at all)",
        "wording_source": "MasterQuestionnaire.pdf Q59 'Your neighborhood'; WVS_wave7.dta variable label 'Trust: Your neighborhood'",
        "valid_responses": "1=Trust completely; 2=Trust somewhat; 3=Do not trust very much; 4=Do not trust at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more trust, toward raw 1 'Trust completely' and away from raw 4 'Do not trust at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source. Config label: 'Trust: Your neighborhood (1-4 inv)'.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q60",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Trust: people you know personally (1 trust completely … 4 do not trust at all)",
        "wording_source": "MasterQuestionnaire.pdf Q60 'People you know personally'; WVS_wave7.dta variable label 'Trust: People you know personally'. CONSTRUCT_MAP.md short label 'Personal acquaintances' is a paraphrase, not the questionnaire object.",
        "valid_responses": "1=Trust completely; 2=Trust somewhat; 3=Do not trust very much; 4=Do not trust at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more trust, toward raw 1 'Trust completely' and away from raw 4 'Do not trust at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source. Config label: 'Trust: Personal acquaintances (1-4 inv)'.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q61",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Trust: people you meet for the first time (1 trust completely … 4 do not trust at all)",
        "wording_source": "MasterQuestionnaire.pdf Q61; WVS_wave7.dta variable label 'Trust: People you meet for the first time'",
        "valid_responses": "1=Trust completely; 2=Trust somewhat; 3=Do not trust very much; 4=Do not trust at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more trust, toward raw 1 'Trust completely' and away from raw 4 'Do not trust at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source. Config label: 'Trust: People met first time (1-4 inv)'.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q62",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Trust: people of another religion (1 trust completely … 4 do not trust at all)",
        "wording_source": "MasterQuestionnaire.pdf Q62; WVS_wave7.dta variable label 'Trust: People of another religion'",
        "valid_responses": "1=Trust completely; 2=Trust somewhat; 3=Do not trust very much; 4=Do not trust at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more trust, toward raw 1 'Trust completely' and away from raw 4 'Do not trust at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source. Config label: 'Trust: Other religion (1-4 inv)'.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q63",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Trust: people of another nationality (1 trust completely … 4 do not trust at all)",
        "wording_source": "MasterQuestionnaire.pdf Q63; WVS_wave7.dta variable label 'Trust: People of another nationality'",
        "valid_responses": "1=Trust completely; 2=Trust somewhat; 3=Do not trust very much; 4=Do not trust at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more trust, toward raw 1 'Trust completely' and away from raw 4 'Do not trust at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source. Config label: 'Trust: Other nationality (1-4 inv)'.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q64",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Confidence: the churches (1 a great deal … 4 none at all). Questionnaire prints 'The [churches]1' with footnote: replace with the relevant cultural term.",
        "wording_source": "MasterQuestionnaire.pdf Q64 and footnote 1; WVS_wave7.dta variable label 'Confidence: Churches'",
        "valid_responses": "1=A great deal; 2=Quite a lot; 3=Not very much; 4=None at all",
        "valid_source": "MasterQuestionnaire.pdf confidence stem; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more confidence, toward raw 1 'A great deal' and away from raw 4 'None at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source. Config label: 'Confidence: Churches (1-4 inv)'.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q73",
        "gps_dimension": "trust",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Confidence: parliament (1 a great deal … 4 none at all)",
        "wording_source": "MasterQuestionnaire.pdf Q73 'Parliament'; WVS_wave7.dta variable label 'Confidence: Parliament'",
        "valid_responses": "1=A great deal; 2=Quite a lot; 3=Not very much; 4=None at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more confidence, toward raw 1 'A great deal' and away from raw 4 'None at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS trust",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Generalized, interpersonal, and institutional trust/confidence'. Item-level paper rationale: not stated in source. Config label: 'Confidence: Parliament (1-4 inv)'.",
        "status": "not designated in source",
        "status_note": "In the primary trust composite. Paper does not label this item primary/direct or exploratory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q43",
        "gps_dimension": "patience",
        "rectangle": "primary",
        "codes": SCALE_1_3,
        "kind": "raw",
        "wording": "Less importance placed on work in our lives: good (1) / don't mind (2) / bad (3)",
        "wording_source": "MasterQuestionnaire.pdf Q43; WVS_wave7.dta variable label 'Future changes: Less importance placed on work'",
        "valid_responses": "1=Good; 2=Don't mind; 3=Bad",
        "valid_source": "MasterQuestionnaire.pdf prints 'Good / Don't mind / Bad'. WVS_wave7.dta value labels: 1=Good thing; 2=Don't mind; 3=Bad thing. question_map_wvs_edited.csv matches the dta labels. Endpoint wording differs; codes 1, 2, 3 agree.",
        "direction": "Larger recoded score means closer to 'Bad' (code 3) and away from 'Good' (code 1) for less importance placed on work. Raw code retained. Paper does not state what a larger score means; it says original coding is retained (results.tex).",
        "gps_link": "GPS patience, separate row, not pooled with Q50",
        "gps_rationale": "Paper (results.tex tab:map): patience row, 'Less importance placed on work; financial satisfaction', items interpreted separately. Item-level (results.tex): 'Q43 concerns reduced importance of work'. Original coding retained; the two-item mean is not treated as a validated patience measure. Config (CONSTRUCT_MAP.md): 'Less importance on work: good/bad (1-3)', patience prior directional, not a Falk-validated item.",
        "status": "exploratory bridge",
        "status_note": "Paper (results.tex): 'The other mappings are exploratory bridges, especially where Wave 7 has no direct counterpart to the preference measure.' Applied here as a group label for non-trust tab:map mappings, not as an item-by-item designation.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "Separate row. Not pooled with Q50 (results.tex; STRICT_ITEMS lists them as two patience items).",
    },
    {
        "wvs_id": "Q50",
        "gps_dimension": "patience",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "raw",
        "wording": "Satisfaction with the financial situation of the household (1 completely dissatisfied … 10 completely satisfied)",
        "wording_source": "MasterQuestionnaire.pdf Q50. WVS_wave7.dta variable label: 'Satisfaction with financial situation of household'. Endpoint labels disagree: questionnaire 'Completely dissatisfied/satisfied'; dta value labels 'Dissatisfied/Satisfied'.",
        "valid_responses": "Codes 1-10. Questionnaire: 1=Completely dissatisfied; 10=Completely satisfied; intermediate codes unlabeled on the card. Stata value labels: 1=Dissatisfied; 2-9=the digit; 10=Satisfied. Codes agree; endpoint wording disagrees. Not resolved.",
        "valid_source": "MasterQuestionnaire.pdf Q50; WVS_wave7.dta value labels; question_map_wvs_edited.csv matches the questionnaire endpoints",
        "direction": "Larger recoded score means more financial satisfaction, toward code 10. Both sources put the satisfied pole at 10 and the dissatisfied pole at 1, so the direction agrees even though the endpoint words differ. Raw code retained. Paper does not state the direction of the score; it says original coding is retained.",
        "gps_link": "GPS patience, separate row, not pooled with Q43",
        "gps_rationale": "Paper (results.tex tab:map and the patience paragraph): 'Q50 concerns financial satisfaction'. Reported separately from Q43; two-item mean not treated as a validated patience measure. Config: 'Financial satisfaction (1-10)', tier 3, patience prior LOW.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' for the other mappings (results.tex). Not an item-by-item designation. Config calls the patience dimension directional, not exploratory; that vocabulary difference is recorded, not resolved.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "Separate row. Not pooled with Q43.",
    },
    {
        "wvs_id": "Q106",
        "gps_dimension": "risktaking",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "raw",
        "wording": "Incomes should be made more equal (1) vs greater incentives for individual effort (10)",
        "wording_source": "MasterQuestionnaire.pdf Q106. WVS_wave7.dta variable label is truncated ('…incentives for indi'); value labels 1 and 10 match the questionnaire poles.",
        "valid_responses": "1=Incomes should be made more equal; 2-9 unlabeled on the card (stata labels them with the digit); 10=There should be greater incentives for individual effort",
        "valid_source": "MasterQuestionnaire.pdf Q106; WVS_wave7.dta value labels. question_map_wvs_edited.csv ResponseLabels is empty for this item; ResponseCodes are 1-10.",
        "direction": "Larger recoded score means closer to 'greater incentives for individual effort' (10) and away from 'incomes should be made more equal' (1). Raw code retained. Paper does not state this direction.",
        "gps_link": "GPS risk taking",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Economic values and fare avoidance'. Item-level paper rationale: not stated in source. Config (CONSTRUCT_MAP.md): economic-values scale, incomes equal vs incentives; related to risk-taking in attitude space, not validated against GPS risk. Wave 7 has no direct counterpart to the Falk risk item.",
        "status": "exploratory bridge",
        "status_note": "Paper: 'The other mappings are exploratory bridges, especially where Wave 7 has no direct counterpart to the preference measure.'",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q107",
        "gps_dimension": "risktaking",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "raw",
        "wording": "Private ownership of business and industry should be increased (1) vs government ownership of business and industry should be increased (10)",
        "wording_source": "MasterQuestionnaire.pdf Q107. Stata variable label says 'Private vs state ownership of business'. Stata value labels omit 'and industry' ('Private ownership of business should be increased' / 'Government ownership of business should be increased'). Not resolved.",
        "valid_responses": "Codes 1-10. Questionnaire poles: 1=private ownership of business and industry should be increased; 10=government ownership of business and industry should be increased. Stata value-label poles omit 'and industry'. Intermediate codes unlabeled on the card.",
        "valid_source": "MasterQuestionnaire.pdf Q107; WVS_wave7.dta value labels. question_map ResponseLabels empty; ResponseCodes 1-10.",
        "direction": "Larger recoded score means closer to increased government ownership (code 10) and away from increased private ownership (code 1). Raw code retained. Paper does not state this direction. Pole wording differs between questionnaire and stata; both put government/state ownership at the high code.",
        "gps_link": "GPS risk taking",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Economic values and fare avoidance'. Item-level paper rationale: not stated in source. Config: 'Private ownership (1) vs govt (10)'; not a validated GPS-risk item.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q109",
        "gps_dimension": "risktaking",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "raw",
        "wording": "Competition is good (1) vs competition is harmful (10)",
        "wording_source": "MasterQuestionnaire.pdf Q109; WVS_wave7.dta value labels match those poles. Variable label: 'Competition good or harmful'.",
        "valid_responses": "1=Competition is good; 2-9 unlabeled on the card (stata labels them with the digit); 10=Competition is harmful",
        "valid_source": "MasterQuestionnaire.pdf Q109; WVS_wave7.dta value labels. question_map ResponseLabels empty; ResponseCodes 1-10.",
        "direction": "Larger recoded score means closer to 'Competition is harmful' (10) and away from 'Competition is good' (1). Raw code retained. Paper does not state this direction.",
        "gps_link": "GPS risk taking",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Economic values and fare avoidance'. Item-level paper rationale: not stated in source. Config: 'Competition good (1) vs harmful (10)'; not a validated GPS-risk item.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q178",
        "gps_dimension": "risktaking",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "raw",
        "wording": "Justifiable: avoiding a fare on public transport (1 never justifiable … 10 always justifiable)",
        "wording_source": "MasterQuestionnaire.pdf Q178 under the justifiability stem; WVS_wave7.dta variable label 'Justifiable: Avoiding a fare on public transport'",
        "valid_responses": "1=Never justifiable; 2-9 unlabeled on the card (stata labels them with the digit); 10=Always justifiable",
        "valid_source": "MasterQuestionnaire.pdf justifiability card; WVS_wave7.dta value labels; question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more justifiability of fare avoidance, toward 10 'Always justifiable'. Raw code retained (not in the 11-v set). Paper does not state this direction.",
        "gps_link": "GPS risk taking",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Economic values and fare avoidance'. Item-level paper rationale: not stated in source. Config: 'Justifiable: fare avoidance (1-10)', no inv flag; norm-permissiveness item, not validated against GPS risk.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q81",
        "gps_dimension": "posrecip",
        "rectangle": "primary",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Confidence: charitable or humanitarian organizations (1 a great deal … 4 none at all)",
        "wording_source": "MasterQuestionnaire.pdf Q81; WVS_wave7.dta variable label 'Confidence: Charitable or humanitarian organizations'",
        "valid_responses": "1=A great deal; 2=Quite a lot; 3=Not very much; 4=None at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more confidence, toward raw 1 'A great deal' and away from raw 4 'None at all'. Derived from g(v)=5-v and those labels.",
        "gps_link": "GPS positive reciprocity",
        "gps_rationale": "Paper (results.tex tab:map): 'Confidence in charitable organizations'. Item-level paper rationale beyond that cell: not stated in source. Config: confidence in charitable organizations is a theory bridge; Falk et al. found no WVS positive-reciprocity questions. Positive reciprocity has only Q81 on the strict panel (results.tex).",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges', especially where Wave 7 has no direct counterpart (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q176",
        "gps_dimension": "negrecip",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "raw",
        "wording": "Agree/disagree: nowadays one often has trouble deciding which moral rules are the right ones to follow (1 completely agree … 10 completely disagree)",
        "wording_source": "MasterQuestionnaire.pdf Q176. WVS_wave7.dta variable label is truncated after 'moral rules a'.",
        "valid_responses": "1=Completely agree; 2-9 unlabeled on the card (stata labels them with the digit); 10=Completely disagree",
        "valid_source": "MasterQuestionnaire.pdf Q176; WVS_wave7.dta value labels; question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more disagreement with the trouble-deciding statement, toward 10 'Completely disagree'. Raw code retained. Paper does not state this direction. The tab:map phrase 'moral clarity' is a proposed interpretation, not a stated scoring direction.",
        "gps_link": "GPS negative reciprocity",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Moral clarity and justifiability judgments'. Item-level paper rationale: not stated in source. Config: 'Moral clarity (1-10)'; indirect relative to costly-punishment negative reciprocity.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex). Config calls negrecip a stretch/theory bridge.",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q177",
        "gps_dimension": "negrecip",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "inv10",
        "wording": "Justifiable: claiming government benefits to which you are not entitled (1 never … 10 always)",
        "wording_source": "MasterQuestionnaire.pdf Q177; WVS_wave7.dta variable label 'Justifiable: Claiming government benefits to which you are not entitled'",
        "valid_responses": "1=Never justifiable; 2-9 unlabeled on the card (stata labels them with the digit); 10=Always justifiable",
        "valid_source": "MasterQuestionnaire.pdf; WVS_wave7.dta value labels; question_map_wvs_edited.csv",
        "direction": "Larger recoded score means less justifiability, toward raw 1 'Never justifiable' and away from raw 10 'Always justifiable'. Derived from g(v)=11-v and those labels. Config comment (06_construct_bridge.py): higher raw = more justifiable, so 11-raw.",
        "gps_link": "GPS negative reciprocity",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Moral clarity and justifiability judgments'. Item-level paper rationale: not stated in source. Config: justifiability of claiming benefits; theory bridge to costly punishment, not a validated GPS proxy.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q179",
        "gps_dimension": "negrecip",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "inv10",
        "wording": "Justifiable: stealing property (1 never … 10 always)",
        "wording_source": "MasterQuestionnaire.pdf Q179; WVS_wave7.dta variable label 'Justifiable: Stealing property'",
        "valid_responses": "1=Never justifiable; 2-9 unlabeled on the card (stata labels them with the digit); 10=Always justifiable",
        "valid_source": "MasterQuestionnaire.pdf; WVS_wave7.dta value labels; question_map_wvs_edited.csv",
        "direction": "Larger recoded score means less justifiability, toward raw 1 'Never justifiable' and away from raw 10 'Always justifiable'. Derived from g(v)=11-v and those labels.",
        "gps_link": "GPS negative reciprocity",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Moral clarity and justifiability judgments'. Item-level paper rationale: not stated in source. Config: justifiability of stealing; theory bridge, not a validated GPS proxy.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q195",
        "gps_dimension": "negrecip",
        "rectangle": "primary",
        "codes": SCALE_1_10,
        "kind": "raw",
        "wording": "Justifiable: death penalty (1 never … 10 always)",
        "wording_source": "MasterQuestionnaire.pdf Q195; WVS_wave7.dta variable label 'Justifiable: Death penalty'",
        "valid_responses": "1=Never justifiable; 2-9 unlabeled on the card (stata labels them with the digit); 10=Always justifiable",
        "valid_source": "MasterQuestionnaire.pdf; WVS_wave7.dta value labels; question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more justifiability of the death penalty, toward 10 'Always justifiable'. Raw code retained. Unlike Q177 and Q179, this item is not in the 11-v set. Paper does not state why. Config label has no inv flag.",
        "gps_link": "GPS negative reciprocity",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Moral clarity and justifiability judgments'. Item-level paper rationale: not stated in source. Config: death-penalty justifiability is indirect.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q99",
        "gps_dimension": "altruism",
        "rectangle": "primary",
        "codes": MEMBER,
        "kind": "raw",
        "wording": "Membership: environmental organization (2 active member / 1 inactive member / 0 don't belong)",
        "wording_source": "MasterQuestionnaire.pdf Q99. Stem says 'not a member'; code header says 'Don't belong'. WVS_wave7.dta variable label 'Active/Inactive membership: Environmental organization'; value label 0='Don't belong'.",
        "valid_responses": "2=Active member; 1=Inactive member; 0=Don't belong (questionnaire code header and stata). Questionnaire stem also says 'not a member' for the battery.",
        "valid_source": "MasterQuestionnaire.pdf membership battery; WVS_wave7.dta value labels; question_map_wvs_edited.csv codes 2; 1; 0",
        "direction": "Larger recoded score means more active membership (2 active > 1 inactive > 0 don't belong). Raw code retained, including valid 0 (appendix.tex). Paper does not state this direction.",
        "gps_link": "GPS altruism",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Membership in environmental, charitable, and self-help groups'. Item-level paper rationale: not stated in source. Config: voluntary-organization membership; the Falk altruism item is absent from Wave 7; membership also reflects organizational density.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges', especially where Wave 7 has no direct counterpart (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q101",
        "gps_dimension": "altruism",
        "rectangle": "primary",
        "codes": MEMBER,
        "kind": "raw",
        "wording": "Membership: humanitarian or charitable organization (2 active / 1 inactive / 0 don't belong or not a member)",
        "wording_source": "MasterQuestionnaire.pdf Q101 'Humanitarian or charitable organization'. Code header 'Don't belong'; stem 'not a member'. Stata value label 0 is 'Not a member' (unlike Q99 and Q103, which are 'Don't belong'). Not resolved.",
        "valid_responses": "2=Active member; 1=Inactive member; 0=Don't belong (questionnaire code header and question_map) and 0=Not a member (WVS_wave7.dta value label for Q101 only). Codes 0, 1, 2 agree.",
        "valid_source": "MasterQuestionnaire.pdf; WVS_wave7.dta value labels; question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more active membership (2 > 1 > 0). Raw code retained, including valid 0. The code-0 label disagrees across sources; both labels are the non-member pole, so the direction does not depend on which label is used.",
        "gps_link": "GPS altruism",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Membership in environmental, charitable, and self-help groups'. Item-level paper rationale: not stated in source. Config: member of a charitable organization; exploratory, not the Falk altruism item.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q103",
        "gps_dimension": "altruism",
        "rectangle": "primary",
        "codes": MEMBER,
        "kind": "raw",
        "wording": "Membership: self-help group, mutual aid group (2 active / 1 inactive / 0 don't belong)",
        "wording_source": "MasterQuestionnaire.pdf Q103; WVS_wave7.dta variable label 'Active/Inactive membership: self-help group, mutual aid group'",
        "valid_responses": "2=Active member; 1=Inactive member; 0=Don't belong (questionnaire code header and stata). Stem also says 'not a member'.",
        "valid_source": "MasterQuestionnaire.pdf; WVS_wave7.dta value labels; question_map_wvs_edited.csv",
        "direction": "Larger recoded score means more active membership (2 > 1 > 0). Raw code retained, including valid 0. Paper does not state this direction.",
        "gps_link": "GPS altruism",
        "gps_rationale": "Paper group rationale (results.tex tab:map): 'Membership in environmental, charitable, and self-help groups'. Item-level paper rationale: not stated in source. Config: self-help group membership; exploratory.",
        "status": "exploratory bridge",
        "status_note": "Paper group label 'exploratory bridges' (results.tex).",
        "common_support": "Strict common-support panel: tab:map item set used for every country and arm (appendix.tex). Not among the items removed for Egypt (Q69-Q71) or Great Britain (Q174).",
        "aggregation": "",
    },
    {
        "wvs_id": "Q69",
        "gps_dimension": "trust",
        "rectangle": "sensitivity",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Confidence: the police (1 a great deal … 4 none at all)",
        "wording_source": "MasterQuestionnaire.pdf Q69 'The police'; WVS_wave7.dta variable label 'Confidence: The Police'",
        "valid_responses": "1=A great deal; 2=Quite a lot; 3=Not very much; 4=None at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Not resolved. If g(v)=5-v (script only): larger means more confidence, toward raw 1 'A great deal'. If the raw code were kept (tex does not say this): larger means less confidence, toward raw 4 'None at all'.",
        "gps_link": "GPS trust, sensitivity only, outside the primary rectangle",
        "gps_rationale": "Not in results.tex tab:map. Appendix calls Q69-Q71 institutional items in the Egypt sensitivity ('when the institutional items are restored'). Config label: 'Confidence: Police (1-4 inv)'. Item-level paper rationale for the GPS link: not stated in source beyond that institutional-trust sensitivity.",
        "status": "sensitivity only",
        "status_note": "Outside the primary rectangle. egypt_robustness.tex: not asked in Egypt, omitted everywhere from the primary panel. results.tex: no valid Egypt observations, removed everywhere.",
        "common_support": "Egypt was not asked Q69-Q71 (tables/egypt_robustness.tex). results.tex: Egypt has no valid Q69-Q71 observations, so these items are removed everywhere from the primary comparison. Not in STRICT_ITEMS.",
        "aggregation": "Not in the primary nine-item trust composite.",
    },
    {
        "wvs_id": "Q70",
        "gps_dimension": "trust",
        "rectangle": "sensitivity",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Confidence: the courts (1 a great deal … 4 none at all)",
        "wording_source": "MasterQuestionnaire.pdf Q70 'The courts'; WVS_wave7.dta variable label 'Confidence: Justice System/Courts'",
        "valid_responses": "1=A great deal; 2=Quite a lot; 3=Not very much; 4=None at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv. Stata variable label says 'Justice System/Courts'; questionnaire object is 'The courts'.",
        "direction": "Not resolved. If g(v)=5-v (script only): larger means more confidence, toward raw 1 'A great deal'. If the raw code were kept (tex does not say this): larger means less confidence, toward raw 4 'None at all'.",
        "gps_link": "GPS trust, sensitivity only, outside the primary rectangle",
        "gps_rationale": "Not in results.tex tab:map. Appendix treats Q69-Q71 as institutional items in the Egypt sensitivity. Config label: 'Confidence: Courts (1-4 inv)'. Item-level paper rationale: not stated in source beyond that.",
        "status": "sensitivity only",
        "status_note": "Outside the primary rectangle because Egypt was not asked these items.",
        "common_support": "Egypt was not asked Q69-Q71 (tables/egypt_robustness.tex). Removed everywhere from the primary comparison (results.tex). Not in STRICT_ITEMS.",
        "aggregation": "Not in the primary nine-item trust composite.",
    },
    {
        "wvs_id": "Q71",
        "gps_dimension": "trust",
        "rectangle": "sensitivity",
        "codes": SCALE_1_4,
        "kind": "inv4",
        "wording": "Confidence: the government (1 a great deal … 4 none at all)",
        "wording_source": "MasterQuestionnaire.pdf Q71 'The government'; WVS_wave7.dta variable label 'Confidence: The Government'",
        "valid_responses": "1=A great deal; 2=Quite a lot; 3=Not very much; 4=None at all",
        "valid_source": "MasterQuestionnaire.pdf; same labels in WVS_wave7.dta and question_map_wvs_edited.csv",
        "direction": "Not resolved. If g(v)=5-v (script only): larger means more confidence, toward raw 1 'A great deal'. If the raw code were kept (tex does not say this): larger means less confidence, toward raw 4 'None at all'.",
        "gps_link": "GPS trust, sensitivity only, outside the primary rectangle",
        "gps_rationale": "Not in results.tex tab:map. Appendix treats Q69-Q71 as institutional items in the Egypt sensitivity. Config label: 'Confidence: Government (1-4 inv)'. Item-level paper rationale: not stated in source beyond that.",
        "status": "sensitivity only",
        "status_note": "Outside the primary rectangle because Egypt was not asked these items.",
        "common_support": "Egypt was not asked Q69-Q71 (tables/egypt_robustness.tex). Removed everywhere from the primary comparison (results.tex). Not in STRICT_ITEMS.",
        "aggregation": "Not in the primary nine-item trust composite.",
    },
]

RECODE_TEXT = {
    "binary": "g(v)=1{v=1} (script: 1.0 if v==1.0 else 0.0). methodology.tex and appendix.tex agree for Q57.",
    "inv4": "g(v)=5-v. methodology.tex and appendix.tex: 5-v for Q58-Q64, Q73, and Q81. Script INVERT_1_4 matches those retained items.",
    "inv10": "g(v)=11-v. methodology.tex and appendix.tex agree for Q177 and Q179. Script INVERT_10 matches.",
    "raw": "g(v)=v (raw code). methodology.tex and appendix.tex: other retained items keep the raw code. results.tex: Q43 and Q50 keep original coding. Script returns the raw value.",
}

RECODE_Q69 = (
    "Script (22_paper_a_surface.py INVERT_1_4): g(v)=5-v. "
    "methodology.tex and appendix.tex state 5-v for Q58-Q64, Q73, and Q81 only and do not state g(v) for Q69-Q71. "
    "Not resolved."
)

MISSING = (
    "Excluded before recode. Appendix: raw WVS missing codes -1 through -5 and nonfinite values; valid 0 retained. "
    "Script: v>=0 and finite, then recode (also requires W_WEIGHT>0 for the human mean). "
    "See source note: the named missing-code set is not identical across appendix, questionnaire, and stata labels."
)

TOKEN = "not in repo"

FIELDNAMES = [
    "wvs_id",
    "gps_dimension",
    "rectangle",
    "abbreviated_wording",
    "wording_source",
    "wording_in_repo",
    "valid_responses_after_missing_exclusion",
    "valid_responses_source",
    "missing_exclusion",
    "recode_g",
    "direction_larger_recoded_score",
    "direction_source",
    "range_min",
    "range_max",
    "range_source",
    "gps_link",
    "gps_rationale",
    "status",
    "status_note",
    "common_support",
    "aggregation_note",
    "candidate_response_codes_equal_token_length",
]


def main() -> None:
    assert len(ROWS) == 26
    ids = [r["wvs_id"] for r in ROWS]
    assert len(ids) == len(set(ids))
    out_rows = []
    for r in ROWS:
        lo, hi = rng(r["codes"], r["kind"])
        if r["wvs_id"] in {"Q69", "Q70", "Q71"}:
            lo_raw, hi_raw = rng(r["codes"], "raw")
            assert (lo, hi) == (lo_raw, hi_raw) == (1.0, 4.0)
            recode = RECODE_Q69
            range_source = (
                "Computed from valid codes 1-4. Both g(v)=5-v and g(v)=v map that set onto 1-4, "
                "so the range does not resolve the recode silence."
            )
        else:
            recode = RECODE_TEXT[r["kind"]]
            range_source = (
                "Computed from the valid non-missing codes and g(v). "
                "Not copied from a file."
            )
        out_rows.append({
            "wvs_id": r["wvs_id"],
            "gps_dimension": r["gps_dimension"],
            "rectangle": r["rectangle"],
            "abbreviated_wording": r["wording"],
            "wording_source": r["wording_source"],
            "wording_in_repo": "yes",
            "valid_responses_after_missing_exclusion": r["valid_responses"],
            "valid_responses_source": r["valid_source"],
            "missing_exclusion": MISSING,
            "recode_g": recode,
            "direction_larger_recoded_score": r["direction"],
            "direction_source": "Derived from codebook/questionnaire labels and g(v). Not a paper sentence unless the cell says so.",
            "range_min": f"{lo:g}",
            "range_max": f"{hi:g}",
            "range_source": range_source,
            "gps_link": r["gps_link"],
            "gps_rationale": r["gps_rationale"],
            "status": r["status"],
            "status_note": r["status_note"],
            "common_support": r["common_support"],
            "aggregation_note": r["aggregation"],
            "candidate_response_codes_equal_token_length": TOKEN,
        })

    csv_path = OUT / "item_measurement_table.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    n_in = sum(1 for row in out_rows if row["wording_in_repo"] == "yes")
    n_miss = sum(1 for row in out_rows if row["wording_in_repo"] != "yes")
    md = render_md(out_rows, n_in, n_miss)
    md_path = OUT / "ITEM_TABLE.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"rows={len(out_rows)} wording_in_repo={n_in} wording_missing={n_miss}")
    print(csv_path)
    print(md_path)


def render_md(rows: list[dict], n_in: int, n_miss: int) -> str:
    lines = []
    a = lines.append
    a("# Item measurement table")
    a("")
    a("26 item rows: 23 in `STRICT_ITEMS` (the primary rectangle) and Q69, Q70, Q71 as sensitivity-only rows outside that rectangle. Patience Q43 and Q50 are separate rows, not a pooled composite.")
    a("")
    a(f"Wording found in-repo: {n_in}. Wording missing: {n_miss}.")
    a("")
    a("## Summary")
    a("")
    a("| WVS | GPS link | Rectangle | Abbreviated wording | g(v) | Range | Status |")
    a("|---|---|---|---|---|---|---|")
    for row in rows:
        gshort = {
            "Q57": "1{v=1}",
        }.get(row["wvs_id"])
        if gshort is None:
            if row["wvs_id"] in {"Q69", "Q70", "Q71"}:
                gshort = "script 5-v; tex not stated"
            elif "g(v)=5-v" in row["recode_g"]:
                gshort = "5-v"
            elif "g(v)=11-v" in row["recode_g"]:
                gshort = "11-v"
            else:
                gshort = "v"
        wording = row["abbreviated_wording"].replace("|", "/")
        a(
            f"| {row['wvs_id']} | {row['gps_link'].replace('|', '/')} | {row['rectangle']} | {wording} | {gshort} | {row['range_min']}–{row['range_max']} | {row['status']} |"
        )
    a("")
    a("## Detail")
    a("")
    a("| WVS | Valid responses after missing exclusion | g(v) | Larger recoded score | GPS rationale | Common support | Token length |")
    a("|---|---|---|---|---|---|---|")
    for row in rows:
        cells = [
            row["wvs_id"],
            row["valid_responses_after_missing_exclusion"],
            row["recode_g"],
            row["direction_larger_recoded_score"],
            row["gps_rationale"],
            row["common_support"],
            row["candidate_response_codes_equal_token_length"],
        ]
        a("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |")
    a("")
    a("## Q174 note")
    a("")
    a("Q174 is not in `STRICT_ITEMS` and is not a row. results.tex: Great Britain has no valid Q174 observations, so Q174 is removed everywhere from the primary comparison, along with Q69–Q71. egypt_robustness.tex states the Egypt fact as 'not asked'; results.tex states the Egypt fact as 'no valid observations' and the Great Britain fact as 'no valid Q174 observations'. WVS_wave7.dta labels Q174 code −4 as 'Not asked'. Those phrasings are recorded, not reconciled.")
    a("")
    a("## Script versus tex recodes")
    a("")
    a("Retained `STRICT_ITEMS` formulas agree. `22_paper_a_surface.py` `recode_value`: `5-v` if the item is in `INVERT_1_4`, else `11-v` if in `INVERT_10`, else `1` if the item is Q57 and `v==1` else `0` for Q57, else the raw code. Missing values are masked (`v>=0` and finite) before that function is applied.")
    a("")
    a("methodology.tex: Q57 uses `1{v=1}`; Q58–Q64, Q73, and Q81 use `5-v`; Q177 and Q179 use `11-v`; other retained items keep the raw code. appendix.tex states the same maps and says missing codes −1 through −5 and nonfinite values are removed before any transformation, retaining valid zero membership responses. results.tex says Q43 and Q50 keep their original coding and are reported separately.")
    a("")
    a("No contradictory `g(v)` for the 23 retained items. Two non-resolutions:")
    a("")
    a("1. Q69–Q71: the script applies `g(v)=5-v`. methodology.tex and appendix.tex do not state `g(v)` for those items. They are outside the retained set. No winner picked.")
    a("2. Missing-code inventory, not `g(v)`. Script excludes every `v<0`. appendix.tex names −1 through −5. MasterQuestionnaire.pdf general note on the printed pages lists −1 Don't know, −2 No answer/refused, −3 Not applicable (filter), −5 Missing / not applicable for other reasons, and does not list −4. WVS_wave7.dta value labels on these items list −5, −4 Not asked, −2, and −1, and do not label −3. Q107's stored stata label for −1 is `Don't -9:-2`, which was not repaired. All three sources exclude the labeled negative missing codes before recode and keep valid 0. The exact named set is not identical.")
    a("")
    a("Appendix also says a historic Q69–Q71 bridge recoded negative missing values before masking. That is a retired sequence, not the script's current mask-then-recode order. A purple note in appendix.tex says to strike that fault disclaimer. Both the paragraph and the strike note are in the file; neither states `g(v)` for Q69–Q71.")
    a("")
    a("## Source notes for columns not copied from a file")
    a("")
    a("- **abbreviated_wording.** Filled from `data/WVS/MasterQuestionnaire.pdf`, with column labels from `data/WVS/WVS_wave7.dta` and `DPO_eval_WVS/question_map_wvs_edited.csv`. Not invented. Where those sources disagree, the cell says so.")
    a("- **valid_responses.** Non-missing questionnaire/codebook codes. Missing exclusion is the paper's rule, applied to those codes. Label disagreements are left in the cell.")
    a("- **recode_g.** Taken from `analysis/phase2/22_paper_a_surface.py` and checked against `misc/position_paper/rewrite/methodology.tex` and `appendix.tex`. Q69–Q71 are the exception: script only.")
    a("- **direction_larger_recoded_score.** Not a file field. Derived from the labels and `g(v)`. For Q69–Q71 the derivation is stated under both candidate maps.")
    a("- **range_min / range_max.** Computed in `build_item_table.py` from the valid codes and `g(v)`. Not copied from a file.")
    a("- **gps_link / gps_rationale.** Paper quotes from `misc/position_paper/rewrite/results.tex` and `appendix.tex`. Config quotes from `data/merged/CONSTRUCT_MAP.md`, `synthetic_generation/sca2_datagen/config.py` `WVS_ITEM_MAP`, and comments in `analysis/phase2/06_construct_bridge.py`. Where the paper has no item-level rationale, the cell says `not stated in source` for that part.")
    a("- **status.** Paper labels only. `primary/direct` is not used in the paper, so it is not applied. Q57 and Q58–Q64, Q73 are `not designated in source`. Non-trust tab:map items are `exploratory bridge` from the group sentence in results.tex ('The other mappings are exploratory bridges…'). That sentence is group-level; applying it itemwise is noted. Q69–Q71 are `sensitivity only` because they are outside the primary rectangle. Config uses a different vocabulary (confirmatory / directional / exploratory / stretch). That difference is not resolved by overwriting the paper label.")
    a("- **common_support.** From results.tex, appendix.tex, and `tables/egypt_robustness.tex`. Q174 is a note, not a row.")
    a("- **candidate_response_codes_equal_token_length.** `not in repo`. methodology.tex and appendix.tex say candidate completions are a leading space plus a code and that log probabilities are summed without length normalization. No token counts for those codes were found in the repo. String length was not used as a substitute.")
    a("- **aggregation_note.** Q43 and Q50 only, from results.tex: reported separately; the two-item mean is not a validated patience measure.")
    a("")
    a("Repo paths above are under `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/`.")
    a("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
