# Qualitative Triplet Sample Review

Deterministic sample from QC-passed rows in `checkpoint_raw_pairs.jsonl`: one low-contamination example per country and GPS dimension.

- Source rows: 1316
- QC-passed rows: 1249
- Exported balanced sample size: 599 per country

## 1. MEX / altruism / facet: volunteering time

- `chosen_option`: B
- `z_value`: -0.8131
- `m_diff_signed`: -0.8
- `m_diff_abs`: 0.8
- `contamination_ratio`: 0.625

**Scenario**

I've recently joined a professional network, and one of the members is organizing a community
service event, and I'm torn between participating and using the time for my own professional
development. Decision: I can either attend the community service event and contribute my time and
skills or use the time to attend a workshop that could enhance my career prospects. Trade-off:
Participating in the community service event would demonstrate my commitment to social
responsibility, but it would also mean forgoing an opportunity to invest in my own professional
growth.

**Response A**

I choose to attend the community service event because helping others in need aligns with my values.
I believe contributing to the community is essential, and I can find other times to work on my
professional development.

**Response B**

I decide to attend the workshop because advancing my career is a priority right now. While the
community service event is important, I can find other opportunities to give back in the future.

**Generation Reasoning**



**Selection Reasoning**

The profile has a strongly below-average level of altruism (alpha = -0.81), indicating a lower
willingness to give to good causes. Response B, which prioritizes personal career development over
community service, aligns with this lower altruistic tendency. Since the z-score is negative, the
individual is less likely to choose an option that emphasizes helping others, making Response B the
more consistent choice.

## 2. MEX / negrecip / facet: Retribution Tendency

- `chosen_option`: B
- `z_value`: -0.11460000000000001
- `m_diff_signed`: -1.0
- `m_diff_abs`: 1.0
- `contamination_ratio`: 0.6000000000000001

**Scenario**

I've been waiting in line for hours to get into a popular concert, and just as I'm about to enter,
someone cuts in front of me, claiming they were let in by a staff member, which I highly doubt.
Decision: I can choose to confront the person about the suspected line-cutting and potentially miss
the start of the concert, or I can let it go and get in as soon as possible. Trade-off: Confronting
the line-cutter enforces fairness among attendees but could lead to missing part of the event and
engaging in a potentially heated exchange.

**Response A**

I'll call the person out right now. If they really had been let in by staff, they can prove it.
Letting this slide would just encourage more people to jump the queue, and I won't be part of that.

**Response B**

I'll step aside and let them through. The concert is starting soon, and I don't want to risk getting
into an argument that could make me miss the beginning. It's not worth the hassle.

**Generation Reasoning**

Response A loads positively on negrecip because it explicitly seeks to punish the norm violation
through confrontation, expressing indignation at the unfair behavior and aiming to set a precedent
against line-cutting. Response B loads negatively by avoiding confrontation and prioritizing
personal convenience. Both responses remain similar on other traits: both are impatient
(anticipating the concert start), risk-averse (A risks conflict, B risks missing the concert), have
low trust in the situation (A doubts the staff claim, B doubts the value of confrontation), and lack
positive reciprocity (no mention of prior kindness).

**Selection Reasoning**

The profile shows a moderately below-average level of xi_minus (negrecip), indicating a lower
willingness to punish unfair behavior even when costly. Response B, which involves letting the
situation go to avoid conflict and not risk missing the concert, aligns with this disposition. Since
the z-score is negative, the individual is less likely to engage in costly punishment, making
Response B the more appropriate choice.

## 3. MEX / patience / facet: Waiting for rewards

- `chosen_option`: B
- `z_value`: -0.10840000000000001
- `m_diff_signed`: -0.8
- `m_diff_abs`: 0.8
- `contamination_ratio`: 0.125

**Scenario**

As I'm planning my vacation, I need to decide how to spend my free time before the trip. Decision: I
can either spend the next few weekends researching and planning the perfect itinerary or book a pre-
packaged tour that saves me time now but might not be exactly what I want. Trade-off: Taking the
time to carefully plan my trip means giving up immediate relaxation in exchange for a potentially
more enjoyable and tailored experience later.

**Response A**

I decide to spend the next few weekends researching and planning my itinerary. Although it means
forgoing immediate relaxation, I believe the time invested now will lead to a more fulfilling and
customized trip that aligns better with my interests and preferences in the long run.

**Response B**

I choose to book a pre-packaged tour to save time and enjoy some relaxation now. While the tour
might not be perfect, I prefer the immediate convenience and peace of mind over the uncertainty of
planning everything myself later.

**Generation Reasoning**

Response A loads positively on patience by emphasizing deferred gratification and long-term
planning, prioritizing a tailored and fulfilling experience over immediate relaxation. Response B
loads negatively by favoring immediate convenience and relaxation, accepting a less customized
outcome. Both responses maintain a similar tone, perspective, and emotional intensity, with no
significant variation in trust, risk-taking, altruism, positive reciprocity, or negative
reciprocity. The reasoning remains focused on personal preferences and realistic decision-making
without introducing extraneous cues about other traits.

**Selection Reasoning**

The profile has a negative z-score on the patience (delta) dimension (-0.11), indicating a below-
average willingness to defer gratification. Response B (booking a pre-packaged tour for immediate
convenience) loads negatively on patience and aligns with this disposition, as it prioritizes
present enjoyment over delayed, uncertain rewards. Response A (planning for a more fulfilling future
trip) requires deferring gratification, which contradicts the profile's lower patience level.

## 4. MEX / posrecip / facet: Social Obligation

- `chosen_option`: B
- `z_value`: -1.038
- `m_diff_signed`: -0.8
- `m_diff_abs`: 0.8
- `contamination_ratio`: 1.25

**Scenario**

Context: A friend of a friend helped me get a discount on a purchase by giving me their coupon, and
now they're asking for a ride to the airport because their car is in the shop. Decision: I can
either offer to drive them to the airport or tell them I'm not available to drive them. Trade-off:
Giving them a ride would be a way to thank them for the coupon but would also mean waking up early
and dealing with traffic, which would be inconvenient for me.

**Response A**

I'll drive them to the airport. Even though it means waking up early and dealing with traffic, I
want to acknowledge their help with the coupon. It feels important to show appreciation when someone
goes out of their way for you.

**Response B**

I tell them I can't drive them to the airport because I have an early meeting. I appreciate their
help with the coupon, but I don't want to feel obligated to repay it with something that disrupts my
schedule. People help each other sometimes, but I don't keep score.

**Generation Reasoning**

Response A loads positively on positive reciprocity by explicitly acknowledging the favor and
choosing to repay it with a personal cost (early wake-up and traffic). The appreciation is tied
directly to action. Response B loads negatively by refusing to feel obligated, emphasizing that
appreciation doesn't require repayment and that people shouldn't keep score. The responses match on
other traits: both show moderate appreciation (no hostility), have similar schedule constraints,
involve social obligation without extreme altruism, and maintain similar social distance and
specificity in their reasoning.

**Selection Reasoning**

The profile shows a strongly below-average level of xi_plus (posrecip), indicating a low willingness
to return a favor or thank-you gift to someone who helped at personal cost. Response B aligns with
this disposition because it reflects a decision not to reciprocate the favor, even though the person
helped with the coupon. The response explicitly states that the person doesn't want to feel
obligated to repay the favor, which matches the low posrecip score. In contrast, Response A would
require reciprocating the favor, which contradicts the profile's strongly negative z-score on this
dimension.

## 5. MEX / risktaking / facet: Financial Risk Tolerance

- `chosen_option`: B
- `z_value`: -0.1389
- `m_diff_signed`: -0.8
- `m_diff_abs`: 0.8
- `contamination_ratio`: 0.25

**Scenario**

As I prepare to launch my own business, I must decide how to allocate my initial investment between
a stable, low-growth industry and a more volatile market with higher potential returns. Decision: I
can choose to invest in the stable industry, which guarantees a modest but steady income, or take a
chance on the volatile market, which could result in significant profits or substantial losses.
Trade-off: By opting for the volatile market, I may reap greater financial rewards, but I also risk
depleting my resources and jeopardizing the future of my business.

**Response A**

I'll invest in the volatile market. If I play it safe, I might secure a small income but miss out on
the chance to scale my business quickly. I'm willing to tolerate the risk because the potential
gains could position me for long-term success.

**Response B**

I'll invest in the stable industry. A consistent, modest income ensures I can cover my expenses
without jeopardizing my resources. I prefer reliable outcomes over uncertain bets, even if it means
slower growth.

**Generation Reasoning**

Response A loads positively on risk-taking by embracing uncertainty and framing the risky option as
a positive opportunity for growth. It emphasizes the potential gains and willingness to tolerate
risk. Response B loads negatively by preferring a cautious, stable approach and highlighting the
avoidance of risk to protect resources. Both responses share a similar perspective (first person),
tone (pragmatic), emotional intensity (calm), specificity (same scenario details), length, and
stakes (business investment decision). Neither response differs in trust, patience, altruism,
positive reciprocity, or negative reciprocity; both consider the future of the business and make
rational decisions based on their risk preferences.

**Selection Reasoning**

The profile has a z-score of -0.14 on the gamma (risktaking) dimension, indicating a moderately
below-average willingness to take risks. Response B, which loads negatively on the target dimension,
aligns with this disposition by expressing a preference for a stable, low-risk investment. The
individual prefers reliable outcomes over uncertain bets, which is consistent with lower risk
tolerance. Response A, while acknowledging the potential for higher returns, expresses a willingness
to tolerate risk that contradicts the profile's below-average risk-taking tendency.

## 6. MEX / trust / facet: Believing in good intentions

- `chosen_option`: B
- `z_value`: -0.35710000000000003
- `m_diff_signed`: -0.8
- `m_diff_abs`: 0.8
- `contamination_ratio`: 0.875

**Scenario**

I've been asked by a fellow volunteer to handle the donations at our charity event, and I must
decide whether to trust them to manage the finances honestly or to take on the responsibility
myself, which would add to my already heavy workload. The choice is between having faith in their
integrity and potentially losing control over the funds, or maintaining control but overburdening
myself and possibly undermining our collaboration.

**Response A**

I decide to hand over the donation management to my fellow volunteer, trusting they’ll handle the
funds with the same care I would. I’ve seen their dedication to the cause and believe they want
what’s best for the event, even if I can’t monitor every detail. I’ll focus on my main tasks,
confident they’ll keep us on track and honest.

**Response B**

I choose to take the donation management myself, even though it adds to my workload, because I can’t
assume someone else will be equally diligent without oversight. I know I can manage the funds
reliably, and it’s better to be certain than risk mistakes or misallocation. I’ll ask the volunteer
to help with other tasks where I can check their work more easily.

**Generation Reasoning**



**Selection Reasoning**

The profile has a standardized z-score of -0.36 on the tau (trust) dimension, indicating a
moderately below-average level of trust in others' good intentions. Response B, which loads
negatively on the trust dimension, aligns with this disposition by showing a preference for taking
control rather than relying on someone else's integrity. The decision to manage the donations
personally, despite increased workload, reflects a lack of baseline faith in strangers without
institutional enforcement. This choice is consistent with the profile's lower-than-average trust
orientation, as it prioritizes personal oversight over delegation based on assumed good intentions.

## 7. USA / altruism / facet: donating resources

- `chosen_option`: A
- `z_value`: 0.40640000000000004
- `m_diff_signed`: 1.0
- `m_diff_abs`: 1.0
- `contamination_ratio`: 0.4

**Scenario**

I've just received a bonus for meeting my sales targets and am deciding how to use it. Decision: I
can either put the money towards a charity that supports education for underprivileged children or
use it to upgrade my own work equipment to improve my productivity. Trade-off: Donating the money
would contribute to a good cause but would mean forgoing an opportunity to enhance my own
professional capabilities.

**Response A**

I decide to donate the bonus to the education charity. Supporting underprivileged children aligns
with my belief that access to education should not depend on one's background. I know better tools
could help me, but this money will have a more lasting impact on a larger number of people.

**Response B**

I choose to upgrade my work equipment with the bonus. Improving my productivity will allow me to
generate more value for my team in the long run. I believe investing in my own tools is a practical
way to contribute to shared success through personal efficiency.

**Generation Reasoning**

Response A loads positively on altruism by prioritizing the group welfare of underprivileged
children over personal professional development, emphasizing the broader impact of the donation.
Response B loads negatively by focusing on self-investment with an indirect claim about benefiting
the team through personal efficiency, which centers the decision on personal gain. Both responses
maintain similar levels of trust (neither suspicious nor overly trusting), risk-taking (both are
calculated decisions), patience (both consider long-term outcomes), positive reciprocity (both imply
some form of benefit), and negative reciprocity (neither references unfair treatment).

**Selection Reasoning**

The profile shows a strong positive disposition on the alpha (altruism) dimension with a z-score of
+0.41, indicating a willingness to give to good causes and allocate windfall gains to charity.
Response A directly aligns with this by choosing to donate the bonus to an education charity,
emphasizing the lasting impact on a larger number of people. While Response B focuses on self-
improvement and practical contributions, it does not align with the positive loading on the altruism
dimension. Given the clear positive z-score on alpha, Response A is the more appropriate choice.

## 8. USA / negrecip / facet: Self-Sacrifice Willingness

- `chosen_option`: A
- `z_value`: 0.011600000000000001
- `m_diff_signed`: 1.0
- `m_diff_abs`: 1.0
- `contamination_ratio`: 0.8

**Scenario**

I've been waiting in line for hours to get into a popular concert, and just as I'm about to enter,
someone cuts in front of me, claiming they were told to do so by an event staff member. Decision: I
can choose to confront the person and potentially involve the staff, or I can let it go and avoid
any hassle. Trade-off: Confronting the line cutter would punish the unfair behavior, but it might
lead to an unpleasant altercation and delay my own entry.

**Response A**

I step forward and tell the person I saw the staff direct everyone to line up properly. I ask for a
supervisor to check the entry order. Even if I arrive late now, I won't let someone else's shortcut
undermine the rules we all followed.

**Response B**

I let the person pass and keep moving toward the entrance. I don't have time to argue about who
should go first. If they got through faster by following different instructions, maybe they actually
were told to do so.

**Generation Reasoning**

Response A loads positively on negrecip by explicitly seeking to punish the norm violation through
formal channels, even at the cost of personal delay. The speaker shows indignation at the unfair
advantage and wants to enforce the rules. Response B loads negatively by accepting the outcome
without challenge, showing no desire to sanction the behavior despite the unfairness. Both responses
maintain similar levels of trust (not assuming staff corruption), patience (neither is extreme),
risk tolerance (both avoid direct confrontation), altruism (neither offers help to the violator),
and positive reciprocity (neither seeks to reward the fair-behaving staff).

**Selection Reasoning**

The profile shows a near-global-average level of xi_minus (negrecip), which is the willingness to
punish unfair behavior even when costly. Since the z-score is positive (+0.01), the profile
expresses a slightly above-average level of this trait. Response A, which involves confronting the
line cutter and seeking a supervisor to enforce the rules, directly aligns with the willingness to
punish unfair behavior, even if it means a personal cost (delaying one's own entry). Response B,
which involves letting the person pass without confrontation, represents the opposite approach.
Given that the target dimension loads positively on Response A and negatively on Response B, and the
profile shows a slight positive disposition on the target dimension, Response A is the better match.

## 9. USA / patience / facet: Tolerating delays

- `chosen_option`: A
- `z_value`: 0.8113
- `m_diff_signed`: 1.0
- `m_diff_abs`: 1.0
- `contamination_ratio`: 0.1

**Scenario**

I've been wanting to learn a new language and have finally found some time to dedicate to it.
Decision: I can spend my study sessions focusing on basic phrases and vocabulary that I can use
immediately, or delve deeper into the grammar and syntax, which will take longer to pay off but
provide a stronger foundation. Trade-off: Focusing on the deeper aspects of the language means I
won't be able to hold simple conversations as quickly, but it will ultimately allow me to
communicate more effectively and understand more complex texts.

**Response A**

I choose to study grammar and syntax first. Building a strong foundation now means I'll grasp the
language more deeply in the long run, even if I can't chat right away. I'd rather invest my time
where it compounds later.

**Response B**

I'm focusing on basic phrases and vocabulary. I want to start using the language quickly and get
immediate practice. Conversing now keeps me motivated and engaged with the learning process.

**Generation Reasoning**

Response A loads positively on patience (delta) by emphasizing long-term investment in foundational
knowledge, deferring immediate conversational gratification for deeper understanding later. Response
B loads negatively by prioritizing immediate practical use and motivation from quick feedback. Both
responses maintain similar levels of trust (no social judgments), risk-taking (no high-stakes
gambles), altruism (no consideration of others' needs), positive/negative reciprocity (no social
exchanges), and emotional tone (both are neutral and goal-oriented).

**Selection Reasoning**

The profile shows a strong preference for patience (delta = +0.81), indicating a willingness to
defer gratification for long-term benefits. Response A aligns with this by prioritizing grammar and
syntax for deeper understanding, even though it delays immediate conversation skills. Response B,
which focuses on quick, practical phrases for immediate use, contradicts the positive loading on
patience and thus is less aligned with the profile.

## 10. USA / posrecip / facet: Interpersonal Debt Repayment

- `chosen_option`: A
- `z_value`: 0.20370000000000002
- `m_diff_signed`: 0.7000000000000001
- `m_diff_abs`: 0.7000000000000001
- `contamination_ratio`: 0.5714

**Scenario**

Context: A friend of a friend, who is a skilled mechanic, fixes my bike for free when I'm in a
pinch, saving me from a long and expensive repair bill. Decision: When I later find out they're
looking for someone to pet-sit for them while they're away, I can either offer to take care of their
pet or recommend someone else who might be interested. Trade-off: Taking on the pet-sitting
responsibility would be a direct way to return their kindness but requires a significant time
commitment and responsibility on my part.

**Response A**

I offer to pet-sit for them. It's the least I can do after they spent time fixing my bike when I
needed it most.

**Response B**

I recommend someone else for pet-sitting. I'm not sure I have the time, and I don't want to take on
more than I can handle.

**Generation Reasoning**

Response A loads positively on the target dimension by explicitly acknowledging the prior help and
choosing to return the favor directly, which aligns with the posrecip facet of expressing
appreciation and assuming cooperative intentions. Response B loads negatively by declining the
responsibility and redirecting it to another person, without acknowledging or attempting to repay
the initial kindness. Both responses maintain similar levels of trust (no explicit distrust), risk-
taking (both consider personal costs), patience (neither shows impatience), altruism (both consider
helping but differ in execution), positive reciprocity (A is high, B is low), and negative
reciprocity (not relevant here).

**Selection Reasoning**

The profile has a positive z-score of +0.20 on xi_plus (posrecip), indicating a moderate willingness
to return a favor. Response A directly reflects this by offering to pet-sit as a way to reciprocate
the mechanic's help, aligning with the positive loading on the target dimension. While the profile's
delta (patience) is strongly positive, suggesting a willingness to commit time, and alpha (altruism)
is also positive, these are secondary considerations. The key factor is the positive xi_plus score,
which makes Response A the more aligned choice.

## 11. USA / risktaking / facet: Physical Danger Acceptance

- `chosen_option`: A
- `z_value`: 0.11660000000000001
- `m_diff_signed`: 1.0
- `m_diff_abs`: 1.0
- `contamination_ratio`: 0.0

**Scenario**

I've been offered a chance to participate in a high-altitude mountaineering expedition, which would
be a once-in-a-lifetime experience. Decision: I can either accept the invitation and begin training
for the climb, or decline due to concerns about the physical and mental demands of the expedition.
Trade-off: Embarking on the expedition offers a unique opportunity for personal challenge and
growth, but also exposes me to the dangers of high-altitude climbing, including altitude sickness,
avalanches, and extreme weather conditions.

**Response A**

I'll accept the expedition and start training. The risks are real, but the potential for growth and
the thrill of the climb outweigh the dangers. I see this as a chance to push my limits and embrace
the unknown.

**Response B**

I'll decline the expedition. The risks of altitude sickness, avalanches, and harsh weather are too
great, and I'd rather avoid the uncertainty. My priority is maintaining my health and safety without
unnecessary exposure.

**Generation Reasoning**

Response A loads positively on risktaking (gamma) by embracing uncertainty, framing the risky option
positively (thrill of the climb, potential for growth), and showing willingness to take on physical
danger. Response B loads negatively by emphasizing caution, avoiding uncertainty, and prioritizing
safety over potential gains. Both responses maintain similar levels of trust (no indication of
distrust in the expedition), patience (no long-term planning emphasis), altruism (no prosocial
motivations), positive/negative reciprocity (no social exchange considerations). The emotional
intensity and specificity are matched, with both acknowledging the real dangers but differing in
their evaluation of those risks.

**Selection Reasoning**

The profile shows a moderately above-average willingness to take risks (gamma = +0.12). Response A
aligns with this disposition by acknowledging the risks while emphasizing the potential for growth
and the thrill of the climb, which reflects a positive loading on the risk-taking dimension.
Response B, on the other hand, expresses a preference for avoiding uncertainty and prioritizing
safety, which is a negative loading on the same dimension. Given the positive z-score for gamma,
Response A is more consistent with the profile's risk-taking orientation.

## 12. USA / trust / facet: Giving others the benefit of the doubt

- `chosen_option`: A
- `z_value`: 0.1504
- `m_diff_signed`: 1.0
- `m_diff_abs`: 1.0
- `contamination_ratio`: 0.9

**Scenario**

I have just met a fellow volunteer at a community event who claims to have already signed us up for
a joint project that requires our names to be submitted together. Decision: I can either trust that
this volunteer has indeed signed us up and focus on preparing for the project, or I can take the
time to verify the registration myself, potentially delaying our preparation. Trade-off: Accepting
the volunteer's word saves me time and effort but could lead to us missing the project deadline if
the registration was not completed.

**Response A**

I decide to trust the volunteer's word and focus on preparing for the project. If they made a
mistake or forgot, I can address it later, but right now, preparing effectively is more urgent. I
believe people generally follow through on what they say unless there's a reason not to.

**Response B**

I decide to double-check the registration myself before moving forward with preparations. It only
takes a few minutes, and confirming now could prevent us from missing the deadline later. I prefer
to verify things myself rather than assume someone else has done it correctly.

**Generation Reasoning**

Response A loads positively on the trust dimension by expressing a baseline faith in the volunteer's
good intentions and accepting their assurance without verification. It assumes the volunteer will
follow through and focuses on the higher-priority task of preparation. Response B loads negatively
by prioritizing verification over trust, showing a lower baseline assumption that others will act
reliably without oversight. Both responses are similar on other traits: they acknowledge the same
time cost (A mentions addressing mistakes later, B mentions it taking a few minutes), both are
cautious about the deadline, neither expresses strong altruism or negative reciprocity, and both
maintain a neutral, practical tone without emotional intensity.

**Selection Reasoning**

The profile has a positive z-score of +0.15 on the tau (trust) dimension, indicating a moderately
above-average tendency to believe that others have good intentions and to place baseline faith in
strangers without institutional enforcement. Response A aligns with this disposition by choosing to
trust the volunteer's word and focus on preparation, reflecting the belief that people generally
follow through on their commitments unless there is a reason not to. While the other GPS dimensions
(like delta patience and xi_plus positive reciprocity) provide additional context, the target
dimension of trust is the primary factor here, and the positive sign of the z-score clearly points
toward Response A as the more aligned choice.
