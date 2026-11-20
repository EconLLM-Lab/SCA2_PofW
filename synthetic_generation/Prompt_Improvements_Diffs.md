# Prompt Improvement Diffs

Baseline: prompts used by the latest persisted run available in this repo, `anchored_pilot_v2_20260614_081451Z` (`outputs/anchored_pilot_v2/manifest_600.json`, `sample_size: 600`).  
Baseline code reference: `ecd44f4` (`positive anchors, better prompts, and qwen for selection`).  
Proposed code reference: current prompt code after `ccfb1d8` and `b78458d`.

Note: the manifest in the repo is `sample_size: 600`, not 200 or 360. It contains ARG, SWE, and USA outputs, so this appears to be the latest available run artifact to compare against.

## Facet Generation Prompt

```diff
- You are an expert experimental economist.
+ You are a behavioral scientist who designs realistic decision scenarios.
  Break the cultural trait '{dim_key}' into exactly 5 distinct sub-dimensions (facets).
  Trait description: {dim_info['desc']}
  Return ONLY a valid JSON object, with no markdown or surrounding text, in the form {"facets": ["...", "..."]}.
  Each facet should be short, concrete, and behaviorally distinct.
```

## Scenario Generation Prompt

```diff
- You are an expert experimental economist.
+ You are a behavioral scientist who designs realistic decision scenarios.
  Generate exactly {count} diverse scenarios for the GPS dimension '{dim_key}'.
  Dimension description: {dim_info['desc']}
  Target sub-dimension/facet: {facet}
- Each scenario should be 1 to 3 sentences and describe a concrete decision situation.
- Vary social setting and stakes while staying realistic.
+ Each scenario should describe one concrete decision situation using this exact light template:
+ Context: One realistic sentence establishing the agent, setting, and stakes.
+ Decision: One sentence stating the two behaviorally plausible options the agent is choosing between.
+ Trade-off: One sentence making the core target-facet tension explicit without naming high/low GPS scores.
+ The Decision line must make clear what choice the agent is actually facing.
+ The Trade-off line must make the relevant target dimension/facet easy to infer while avoiding labels like 'high trust' or 'low altruism'.
+ Vary social setting and stakes while staying realistic and culturally neutral.
  Do NOT generate scenarios requiring numerical calculations, lottery-style gambles, or hypothetical pricing decisions.
  {anchor_block}
  Return ONLY a valid JSON object, with no markdown or surrounding text: {"scenarios": ["...", "..."]}.
```

## Triplet Generation Prompt

```diff
- Scenario: {scenario}
+ You are a behavioral scientist who designs realistic decision scenarios.
+
+ CONTEXT
+ Scenario:
+ {scenario}
+
  Target sub-dimension: {facet}
  Target dimension: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}
  Dimension rubric: {dim_info['rubric']}
 
+ TASK
  Generate two opposing responses to this same scenario.
- - Response A should load positively on the target dimension.
- - Response B should load negatively on the target dimension.
- Vary only the target dimension/facet between Response A and Response B; keep the other five GPS traits (trust, risk-taking, patience, altruism, positive reciprocity, and negative reciprocity, excluding the target) as constant as possible.
- The two responses should be nearly identical in tone, length, and behavioral realism except for the specific choices and reasoning that reflect the target dimension.
- Both responses must be 2 to 4 sentences, behaviorally realistic, and written in English.
- Do NOT use phrases like 'As a Mexican' or 'As an American'. Express dispositions through behavioral choices and reasoning patterns, not national identity labels.
- Do not create a strawman response.
+ - Response A should load positively on the target dimension: it should express a higher level of the target trait/facet.
+ - Response B should load negatively on the target dimension: it should express a lower level or absence of the target trait/facet.
+ - Positive loading does not mean morally better, more polite, or more socially desirable.
+ - Negative loading does not mean irrational, careless, hostile, or cartoonishly selfish.
+
+ CONTROL REQUIREMENTS
+ - Vary only the target dimension/facet between Response A and Response B.
+ - Keep the other five GPS traits as constant as possible: trust, risk-taking, patience, altruism, positive reciprocity, and negative reciprocity, excluding the target.
+ - Match the two responses on perspective, tone, emotional intensity, specificity, length, social distance, stakes, and behavioral realism.
+ - Do not let both responses drift toward the high-loading option just because it sounds prudent, prosocial, or cooperative.
+ - Do not introduce extra cues about non-target traits unless the same cue appears in both responses.
+
+ STYLE REQUIREMENTS
+ - Write both responses in first person, present tense.
+ - Use 2 to 3 sentences per response and aim for similar word counts.
+ - Start each response with the concrete decision, then give the reasoning behind that decision.
+ - Do not mention GPS dimensions, profile scores, countries, or national identity labels in either response.
+ - Do NOT use phrases like 'As a Mexican' or 'As an American'. Express dispositions through behavioral choices and reasoning patterns.
+ - Do not create a strawman response; both responses must sound like plausible choices by reasonable people.
  {anchor_block}
+ Reasoning field: Briefly explain (1) how Response A loads positively and Response B loads negatively on the target dimension, and (2) how the two responses remain similar on the other five GPS traits.
  Return ONLY a valid JSON object, with no markdown or surrounding text: {"response_a": "...", "response_b": "...", "reasoning": "..."}
```

## Selection Prompt

```diff
- System message:
- {profile_text}
+ System message:
+ You are a behavioral scientist who designs realistic decision scenarios.
```

```diff
- Scenario: {scenario}
+ You are a behavioral scientist who designs realistic decision scenarios.
+
+ CONTEXT
+ Scenario:
+ {scenario}
+
  Target sub-dimension: {facet}
  Target dimension: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}
- Observed standardized disposition on {dim_key}: {z_c[dim_key]:+.2f}
+ Observed standardized disposition on {dim_key}: {z_value:+.2f}
 
  Profile description:
  {profile_text}
 
+ Fixed response loadings:
+ - Response A was generated to load positively on the target dimension.
+ - Response B was generated to load negatively on the target dimension.
+
  Response A: {response_a}
 
  Response B: {response_b}
 
- Select which fixed response is more aligned with the profile's disposition on the target dimension. The profile has a {z_c[dim_key]:+.2f} standardized score. Choose the response that better matches this specific tendency; pay special attention to the sign of the z-score.
- Do not rewrite either response.
+ TASK
+ Select which fixed response is more aligned with the profile's disposition on the target dimension.
+ - Sign rule: {sign_guidance}
+ - The profile description is supporting context for interpreting the target disposition, not a separate instruction to prefer socially desirable behavior.
+ - Focus on the target dimension first; use the other GPS dimensions only as secondary context when the target signal is near zero or ambiguous.
+ - Please pay special attention to the sign of the z-score. Magnitude affects how strong the explanation should be, but the sign determines the expected direction.
+ - Do not rewrite either response.
+ Reasoning field: Explain which response better matches the profile's disposition on the target dimension and why, paying special attention to the sign of the z-score.
  Return ONLY a valid JSON object, with no markdown or surrounding text: {"chosen_option": "A" or "B", "reasoning": "..."}
```

Added `sign_guidance` branch:

```diff
+ If z > 0:
+   The z-score is positive, so the profile expresses an above-average level of the target trait.
+   Because Response A is the positive-loading option and Response B is the negative-loading option,
+   Response A should be preferred unless the response text clearly contradicts the loading.
+
+ If z < 0:
+   The z-score is negative, so the profile expresses a below-average level of the target trait.
+   Because Response A is the positive-loading option and Response B is the negative-loading option,
+   Response B should be preferred unless the response text clearly contradicts the loading.
+
+ If z == 0:
+   The z-score is exactly zero, so the profile is at the global average on the target trait.
+   Use the profile description to choose the less extreme response, while remembering that
+   Response A is positive-loading and Response B is negative-loading.
```

## Scoring Prompt

```diff
- You are an expert experimental economist scoring responses on six dimensions.
+ You are a behavioral scientist who designs realistic decision scenarios.
+ Score responses on six GPS dimensions using the rubrics below.
 
  DIMENSIONS AND RUBRICS:
  {rubric_block}
 
  SCENARIO: {scenario}
 
  TARGET DIMENSION: {dim_info['symbol']} ({dim_key}) - {dim_info['desc']}
 
  RESPONSE A: {chosen_text}
 
  RESPONSE B: {rejected_text}
 
  Score each response from 0.0 to 1.0 on every dimension. A score of 0.0 means the response expresses the lowest possible level or absence of that trait; a score of 1.0 means the response expresses the highest possible level of that trait.
+ Reasoning field: Briefly justify the scores assigned to both responses, focusing on the target dimension and any notable movement on non-target dimensions.
  Return ONLY a valid JSON object, with no markdown or surrounding text: {"scores_a": {"trust": <float>, "risktaking": <float>, "patience": <float>, "altruism": <float>, "posrecip": <float>, "negrecip": <float>}, "scores_b": {"trust": <float>, "risktaking": <float>, "patience": <float>, "altruism": <float>, "posrecip": <float>, "negrecip": <float>}, "reasoning": "<brief justification>"}
```

## Profile Builder

No code diff: `build_cultural_profile` is identical in the latest run baseline and the proposed code.

```diff
  def build_cultural_profile(z_c: dict[str, float]) -> str:
      """Return an anonymized quantitative cultural profile (no country name)."""
 
      def magnitude(value: float) -> str:
          absolute = abs(value)
          if absolute < 0.10:
              return "near the global average"
          if absolute < 0.40:
              return f"moderately {'above' if value > 0 else 'below'} average"
          return f"strongly {'above' if value > 0 else 'below'} average"
 
      dim_lines = []
      for dim_key, info in GPS_DIMENSIONS.items():
          value = z_c[dim_key]
          dim_lines.append(
              f"- {info['symbol']} ({dim_key}) = {value:+.2f}: {magnitude(value)}. {info['desc']}"
          )
 
      return (
          "GPS CULTURAL STATE VECTOR (Falk et al. 2018, standardized deviations from global mean):\n"
          f"{chr(10).join(dim_lines)}"
      )
```

Concrete example using the USA vector from `manifest_600.json`:

```text
Input z_c:
{
  "trust": 0.15036696195602417,
  "risktaking": 0.11658679693937302,
  "patience": 0.8112621307373047,
  "altruism": 0.40642887353897095,
  "posrecip": 0.20365002751350403,
  "negrecip": 0.011553643271327019
}
```

```text
GPS CULTURAL STATE VECTOR (Falk et al. 2018, standardized deviations from global mean):
- tau (trust) = +0.15: moderately above average. Belief that others have good intentions; baseline faith in strangers without institutional enforcement.
- gamma (risktaking) = +0.12: moderately above average. Willingness to take risks, evaluated via hypothetical staircase lotteries and self-assessment.
- delta (patience) = +0.81: strongly above average. Willingness to defer gratification, evaluated via staircase intertemporal choices.
- alpha (altruism) = +0.41: strongly above average. Willingness to give to good causes and allocate a windfall gain to charity.
- xi_plus (posrecip) = +0.20: moderately above average. Willingness to return a favor or thank-you gift to a stranger who helped at personal cost.
- xi_minus (negrecip) = +0.01: near the global average. Willingness to punish unfair behavior even when costly (for example, rejecting low offers).
```
